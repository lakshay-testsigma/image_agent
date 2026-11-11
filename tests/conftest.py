"""Shared fixtures: a throw-away studio root (assets/, design/, output/) and helpers that drive the real CLI.

Nothing here calls a model. Where the pipeline expects the agent's work (intake JSON, fact extraction, checker
verdicts, a generated image) the helpers write a plausible file, so every deterministic gate runs for real.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from PIL import Image

import studio
from lib import paths

REPO = Path(__file__).resolve().parents[1]

GLOBAL = {
    "name": "test-system",
    "version": "1",
    "style": {
        "theme": "quiet premium",
        "palette": {"primary": ["#111111"], "accent": ["#C8A27A"], "background": "#F5F2EC"},
        "typography": {"headline_font": "Helvetica"},
        "lighting": "soft key light from the left",
        "background": "warm off-white sweep",
        "output": {"aspect": "1:1", "width": 400, "height": 400},
    },
    "generation": {"max_attempts": 2, "variations": 1},
    "must_avoid": ["watermarks"],
    "identity_constraints": ["Never change the subject's shape or colours."],
    "locked": ["style.palette", "generation.max_attempts"],
    "mockups": [{"name": "catalog", "type": "catalog"}, {"name": "lifestyle", "type": "lifestyle"}],
}

BRIEF = """# Brief

## Subject
- What it is: lounge chair
- Brand / owner: Nordlys

## Fidelity
exact

## Known facts (client-approved)
- Height: 85 cm

## Facts to verify / show
height, material

## Creative direction
Calm Scandinavian studio shots.

## Must avoid
<!-- a comment -->
no health claims

## Approved copy (text allowed on images)
- "Handcrafted in Portugal"
- Not tested on animals
"""

INTAKE = {
    "subject": {"type": "product", "category": "furniture / lounge chair", "industry": "homeware"},
    "fidelity": {"mode": "exact", "source": "brief"},
    "facts_needed": {"needed": True, "keys": ["height", "material"]},
    "identity": {"name": "Nordlys lounge chair", "brand": "Nordlys", "model": None, "confidence": "medium",
                 "basis": "brand tag under the seat"},
    "visible_text": [{"text": "NORDLYS", "location": "tag"}],
    "visual": {"shape": "low lounge chair with curved arms", "materials": ["oak", "paper cord"],
               "colors": [{"name": "natural oak", "hex": "#C9A46B"}], "finish": "matte oil"},
    "photos": [{"file": "01-front.png", "angle": "front three-quarter"}],
    "preservation_checklist": ["curved arms", "woven paper-cord seat", "four tapered legs"],
    "people": {"identifiable": False, "consent": "not_applicable"},
}

MANUFACTURER_PAGE = "Nordlys Lounge Chair\nHeight: 85 cm\nFrame: solid white oak\nWeight 6.2 kg\n"
MANUFACTURER_FACTS = [
    {"key": "height", "label": "Height", "value": 85, "unit": "cm", "quote": "Height: 85 cm"},
    {"key": "material", "label": "Material", "value": "solid white oak", "quote": "Frame: solid white oak"},
]


class Studio:
    def __init__(self, root: Path, capsys):
        self.root, self._capsys = root, capsys

    # ── CLI ──
    def run(self, *argv):
        self._capsys.readouterr()
        studio.main([str(a) for a in argv])
        return json.loads(self._capsys.readouterr().out)

    def fails(self, *argv) -> str:
        """Run a command that must stop; returns the error message."""
        with pytest.raises(SystemExit) as e:
            studio.main([str(a) for a in argv])
        self._capsys.readouterr()
        return str(e.value)

    # ── files ──
    def write(self, rel: str, data) -> Path:
        f = self.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(data if isinstance(data, str) else json.dumps(data, indent=2), encoding="utf-8")
        return f

    def read(self, rel: str):
        return json.loads((self.root / rel).read_text(encoding="utf-8"))

    def image(self, rel: str, size=(300, 300), color="#C9A46B") -> Path:
        f = self.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(f)
        return f

    def global_design(self, **changes) -> dict:
        data = {**copy.deepcopy(GLOBAL), **changes}
        self.write("design/global.json", data)
        return data

    def job(self, name="001-oak-chair", photos=("01-front.png",), brief: str | None = BRIEF, design: dict | None = None) -> Path:
        folder = self.root / "assets" / name
        folder.mkdir(parents=True, exist_ok=True)
        for ph in photos:
            self.image(f"assets/{name}/{ph}")
        if brief is not None:
            self.write(f"assets/{name}/brief.md", brief)
        if design is not None:
            self.write(f"assets/{name}/design.json", design)
        return folder

    # ── stages (the agent's part is faked, the scripts are real) ──
    def intake(self, job: Path, **changes) -> dict:
        data = {**copy.deepcopy(INTAKE), **changes}
        self.write(f"output/{job.name}/intake.json", data)
        return self.run("intake", job)

    def add_source(self, job: Path, text: str, tier: str, url: str | None, facts: list[dict], same_product="yes") -> str:
        f = self.write(f"scratch/{abs(hash((text, url)))}.txt", text)
        sid = self.run("add-source", job, "--text-file", f, "--tier", tier, *(["--url", url] if url else []))["id"]
        self.extract(job, sid, facts, same_product)
        return sid

    def extract(self, job: Path, sid: str, facts: list[dict], same_product="yes"):
        inp = self.write(f"output/{job.name}/research/input-{sid}.json", {"same_product": same_product, "facts": facts})
        return self.run("extract", job, "--source", sid, "--input", inp, "--by", "test-extractor")

    def check(self, job: Path, verdicts: dict | None = None):
        """Play the independent checker: `supported` with the extractor's quote as evidence, unless overridden
        per claim id via `verdicts` ({"F2": {"verdict": "not_found"}})."""
        self.run("verify", job, "--prepare")
        quotes = {f["id"]: f["quote"] for f in self.read(f"output/{job.name}/research/facts.draft.json")["facts"]}
        claims = [c for s in self.read(f"output/{job.name}/factcheck/claims.json")["sources"] for c in s["claims"]]
        out = [{"id": c["id"], "verdict": "supported", "evidence": quotes[c["id"]], **(verdicts or {}).get(c["id"], {})}
               for c in claims]
        self.write(f"output/{job.name}/factcheck/verdicts.json", {"checked_by": "test-checker", "verdicts": out})

    def verify(self, job: Path, *args, verdicts: dict | None = None) -> dict:
        self.check(job, verdicts)
        self.run("verify", job, *args)
        return self.read(f"output/{job.name}/factcheck/facts.verified.json")

    def fact(self, verified: dict, key: str, variant: str | None = None) -> dict:
        return next(f for f in verified["facts"] if f["key"] == key and f.get("variant") == variant)

    def ready(self, name="001-oak-chair", design: dict | None = None) -> Path:
        """A job taken through intake → research → fact-check → design → metadata, with a prompt per mockup."""
        if not (self.root / "design/global.json").exists():
            self.global_design()
        job = self.job(name, design=design)
        self.run("init", job)
        self.intake(job)
        self.add_source(job, MANUFACTURER_PAGE, "manufacturer", "https://nordlys.example/chair", MANUFACTURER_FACTS)
        self.extract(job, "S0", [{"key": "height", "label": "Height", "value": 85, "unit": "cm", "quote": "Height: 85 cm"}])
        self.verify(job, "--require", "height,material")
        resolved = self.run("design", job)
        self.run("metadata", job)
        for m in resolved["mockups"]:
            self.write(f"output/{name}/creative/prompts/{m['name']}.md", f"Prompt for {m['name']}: keep the chair exactly.")
        return job

    def render(self, job: Path, shot: str, size=(400, 400), preflight=True) -> Path:
        """Fake one generation: preflight, a blank image standing in for the image tool's output, register."""
        if preflight:
            self.run("preflight", job, "--shot", shot)
        gen = self.image(f"scratch/gen-{shot}-{len(list((self.root / 'scratch').glob('gen-*')))}.png", size, "#888888")
        meta = self.run("register", job, "--shot", shot, "--image", gen, "--prompt", "p", "--engine", "test+fake")
        return self.root / meta["files"][0]

    def approve(self, job: Path, image: Path, **gates) -> dict:
        g = {"factual": "na", "visual": "pass", "creative": "pass", **gates}
        return self.run("qa-mark", job, image, "--factual", g["factual"], "--visual", g["visual"], "--creative", g["creative"])


@pytest.fixture
def st(tmp_path, monkeypatch, capsys) -> Studio:
    root = tmp_path.resolve()
    monkeypatch.setattr(paths, "ROOT", root)
    monkeypatch.setattr(paths, "ASSETS", root / "assets")
    monkeypatch.setattr(paths, "OUTPUT", root / "output")
    for d in ("assets", "output", "design", "scratch"):
        (root / d).mkdir()
    return Studio(root, capsys)
