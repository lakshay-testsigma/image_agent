"""OpenAI-compatible chat clients for each model role (research / factcheck / vision).

Each role is configured in .env with <ROLE>_BASE_URL, <ROLE>_API_KEY, <ROLE>_MODEL, so the
research and fact-check models can be DeepSeek, a local Ollama model, or anything else that
speaks the OpenAI chat-completions protocol.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from pathlib import Path

from .paths import die

ROLES = {"research": "RESEARCH", "factcheck": "FACTCHECK", "vision": "VISION"}


def role_config(role: str) -> tuple[str | None, str, str]:
    if role not in ROLES:
        die(f"unknown model role '{role}' (use one of: {', '.join(ROLES)})")
    pre = ROLES[role]
    model = os.getenv(f"{pre}_MODEL", "").strip()
    if not model:
        die(f"{pre}_MODEL is not set in .env — configure the {role} model first (see .env.example).")
    base = os.getenv(f"{pre}_BASE_URL", "").strip() or None
    key = os.getenv(f"{pre}_API_KEY", "").strip() or "not-needed"
    return base, key, model


def role_available(role: str) -> bool:
    return bool(os.getenv(f"{ROLES[role]}_MODEL", "").strip())


def _image_data_url(path: Path, max_side: int = 1536) -> str:
    from PIL import Image

    img = Image.open(path)
    img.thumbnail((max_side, max_side))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def chat(
    role: str,
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    images: list[Path] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    from openai import BadRequestError, OpenAI

    base, key, model = role_config(role)
    client = OpenAI(base_url=base, api_key=key, timeout=float(os.getenv("MODEL_TIMEOUT", "300")))

    content: str | list = user
    if images:
        content = [{"type": "text", "text": user}] + [
            {"type": "image_url", "image_url": {"url": _image_data_url(p)}} for p in images
        ]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
    kwargs: dict = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    if json_mode:
        try:
            r = client.chat.completions.create(
                model=model, messages=messages, response_format={"type": "json_object"}, **kwargs
            )
        except BadRequestError:
            # some models/endpoints reject response_format — fall back to plain output + parsing
            r = client.chat.completions.create(model=model, messages=messages, **kwargs)
    else:
        r = client.chat.completions.create(model=model, messages=messages, **kwargs)
    return r.choices[0].message.content or ""


def parse_json(text: str):
    """Parse JSON from a model reply, tolerating <think> blocks and ``` fences."""
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, flags=re.S)
    if fence:
        t = fence.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(t[start : end + 1])
        except json.JSONDecodeError:
            pass
    die(f"model did not return valid JSON. First 400 chars:\n{t[:400]}")
