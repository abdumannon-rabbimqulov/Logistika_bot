"""Uvicorn uchun development uslubidagi log format (vaqt + token yashirish)."""

from __future__ import annotations

import re

from uvicorn.logging import AccessFormatter, DefaultFormatter

_TOKEN_RE = re.compile(r"(token=)[^&\s\"']+", re.IGNORECASE)


def _redact_tokens(message: str) -> str:
    return _TOKEN_RE.sub(r"\1***", message)


class DevDefaultFormatter(DefaultFormatter):
    def format(self, record) -> str:
        return _redact_tokens(super().format(record))


class DevAccessFormatter(AccessFormatter):
    def format(self, record) -> str:
        return _redact_tokens(super().format(record))
