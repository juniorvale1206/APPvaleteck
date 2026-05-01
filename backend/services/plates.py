"""Validação e normalização de placas brasileiras (antiga + Mercosul)."""
import re
from typing import Optional

_PLATE_OLD_RE = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")
_PLATE_INPUT_RE = re.compile(r"^[A-Z]{3}-?\d[A-Z0-9]\d{2}$")
_PLATE_FUZZY_RE = re.compile(r"\b([A-Z]{3})[-\s]?(\d)([A-Z0-9])(\d{2})\b")


def normalize_plate(p: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (p or "").upper())


def valid_plate(p: str) -> bool:
    s = normalize_plate(p)
    if len(s) != 7:
        return False
    return bool(_PLATE_OLD_RE.match(s))


def extract_plate_from_text(text: str) -> Optional[str]:
    m = _PLATE_FUZZY_RE.search(text.upper())
    if not m:
        return None
    return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}"
