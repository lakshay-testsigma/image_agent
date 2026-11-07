"""Evidence store: every fact must trace back to a saved source text in output/<id>/sources/.

Source tiers (most → least authoritative):
  client        client-approved spec (the brief's "Known facts" section becomes S0)
  manufacturer  official brand page, manual, spec sheet
  gs1           GS1 / Verified by GS1 barcode registry
  distributor   authorised distributor listing
  retailer      other retailers (supplementary only)
  other         anything else (reviews, forums) — never enough on its own
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from . import paths
from .paths import Product, die

TIERS = ["client", "manufacturer", "gs1", "distributor", "retailer", "other"]
AUTHORITATIVE = {"client", "manufacturer", "gs1"}
UA = "Mozilla/5.0 (compatible; ProductStudioResearch/0.1)"


def src_dir(prod: Product) -> Path:
    return prod.work / "sources"


def load_index(prod: Product) -> list[dict]:
    return paths.read_json(src_dir(prod) / "index.json", [])


def save_index(prod: Product, idx: list[dict]) -> None:
    paths.write_json(src_dir(prod) / "index.json", idx)


def source_text(prod: Product, sid: str) -> str:
    f = src_dir(prod) / f"{sid}.txt"
    return f.read_text(encoding="utf-8") if f.exists() else ""


def add_source(
    prod: Product,
    text: str,
    tier: str,
    *,
    url: str | None = None,
    title: str | None = None,
    kind: str = "web",
    sid: str | None = None,
    replace: bool = False,
) -> tuple[dict, bool]:
    """Save a source. Returns (entry, created). Dedupes by content hash and URL."""
    if tier not in TIERS:
        die(f"tier must be one of {TIERS}")
    text = (text or "").strip()
    if not text:
        die("source text is empty")
    digest = hashlib.sha256(text.encode()).hexdigest()
    idx = load_index(prod)

    for s in idx:
        same = s["sha256"] == digest or (url and s.get("url") == url) or (sid and s["id"] == sid)
        if not same:
            continue
        if s["sha256"] == digest or not replace:
            return s, False
        # replace content of an existing source (e.g. brief edited, page re-fetched)
        (src_dir(prod) / f"{s['id']}.txt").write_text(text, encoding="utf-8")
        s.update(sha256=digest, chars=len(text), retrieved_at=paths.now(), tier=tier, title=title or s.get("title"))
        save_index(prod, idx)
        return s, True

    if sid is None:
        nums = [int(s["id"][1:]) for s in idx if s["id"][1:].isdigit()]
        sid = f"S{max(nums, default=0) + 1}"
    f = src_dir(prod) / f"{sid}.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    entry = {
        "id": sid,
        "tier": tier,
        "kind": kind,
        "url": url,
        "title": title,
        "file": paths.rel(f),
        "chars": len(text),
        "sha256": digest,
        "retrieved_at": paths.now(),
    }
    idx.append(entry)
    save_index(prod, idx)
    return entry, True


# ── HTML / PDF → text ────────────────────────────────────────────────────────

class _HTMLText(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "iframe", "canvas"}
    BLOCK = {
        "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
        "table", "ul", "ol", "dl", "dt", "dd", "header", "footer", "main", "aside", "figure", "figcaption",
    }
    META = {"description", "og:title", "og:description", "product:brand", "product:retailer_item_id"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.title = ""
        self.in_title = False
        self.in_jsonld = False
        self.buf: list[str] = []
        self.jsonld: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self.in_jsonld, self.buf = True, []
            return
        if tag in self.SKIP:
            self.skip += 1
            return
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name in self.META and a.get("content"):
                self.meta[name] = a["content"]
        if tag in self.BLOCK:
            self.out.append("\n")
        if tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if self.in_jsonld and tag == "script":
            self.jsonld.append("".join(self.buf))
            self.in_jsonld = False
            return
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if self.in_jsonld:
            self.buf.append(data)
        elif not self.skip:
            if self.in_title:
                self.title += data
            self.out.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    parser = _HTMLText()
    parser.feed(html)
    lines, prev = [], None
    for raw in "".join(parser.out).splitlines():
        line = re.sub(r"[ \t ]+", " ", raw).strip()
        if line and line != prev:
            lines.append(line)
        prev = line
    parts = []
    if parser.meta:
        parts.append("=== PAGE META ===\n" + "\n".join(f"{k}: {v}" for k, v in parser.meta.items()))
    parts.append("=== PAGE TEXT ===\n" + "\n".join(lines))
    blocks = []
    for raw in parser.jsonld:
        try:
            blocks.append(json.dumps(json.loads(raw), indent=1, ensure_ascii=False))
        except json.JSONDecodeError:
            continue
    if blocks:
        parts.append("=== STRUCTURED DATA (JSON-LD) ===\n" + "\n\n".join(blocks)[:20000])
    return parser.title.strip(), "\n\n".join(parts)


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(f"=== PAGE {i} ===\n{(pg.extract_text() or '').strip()}" for i, pg in enumerate(reader.pages, 1))


def fetch_url(url: str, timeout: int = 30) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            charset = r.headers.get_content_charset() or "utf-8"
            data = r.read(20_000_000)
    except Exception as e:  # noqa: BLE001 — report any network failure the same way
        die(
            f"could not fetch {url}: {e}\n"
            "Many shops block scripts. Open the page with your own web tool, save the text to a file, "
            "then run: studio.py add-source <product> --text-file <file> --url <url> --tier <tier>"
        )
    if "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
        return Path(urllib.parse.urlparse(url).path).name, pdf_to_text(data)
    return html_to_text(data.decode(charset, errors="replace"))


def file_to_text(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".pdf":
        return pdf_to_text(path.read_bytes())
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suf in (".html", ".htm"):
        return html_to_text(raw)[1]
    return raw
