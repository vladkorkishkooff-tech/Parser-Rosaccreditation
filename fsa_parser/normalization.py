from __future__ import annotations

import re


_SPACE_RE = re.compile(r"\s+")


def normalize_number(value: object) -> str:
    return _SPACE_RE.sub(" ", str(value or "").strip())
