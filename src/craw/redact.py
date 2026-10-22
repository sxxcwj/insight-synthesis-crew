"""把课题里的联系方式和客户企业名称换成占位符，再送去外部搜索和模型。"""

import os
import re
from pathlib import Path


_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_ID_CARD = re.compile(
    r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"
)
_MOBILE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_MOBILE_SPACED = re.compile(r"(?<!\d)1[3-9]\d(?:[-\s]\d{4}){2}(?!\d)")
_BANK_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){15,22}\d(?!\d)")


def redaction_enabled() -> bool:
    raw = os.getenv("REDACTION_ENABLED")
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def configured_client_names() -> list[str]:
    names: list[str] = []
    raw = os.getenv("REDACTION_CLIENT_NAMES", "")
    for part in re.split(r"[,，;；\n]+", raw):
        name = part.strip()
        if len(name) >= 2:
            names.append(name)

    file_path = os.getenv("REDACTION_CLIENTS_FILE", "").strip()
    if file_path:
        path = Path(file_path)
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                name = line.strip()
                if not name or name.startswith("#") or len(name) < 2:
                    continue
                names.append(name)

    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        deduped.append(name)
    return deduped


def _luhn_ok(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _redact_bank_cards(text: str) -> str:
    def replace(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if 16 <= len(digits) <= 19 and _luhn_ok(digits):
            return "[银行卡号]"
        return match.group(0)

    return _BANK_CANDIDATE.sub(replace, text)


def _redact_client_names(text: str, client_names: list[str]) -> str:
    ordered: list[str] = []
    seen: set[str] = set()
    for name in client_names:
        cleaned = name.strip()
        if len(cleaned) < 2 or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    placeholders = {name: f"[客户企业{index}]" for index, name in enumerate(ordered, 1)}
    for name in sorted(ordered, key=len, reverse=True):
        text = text.replace(name, placeholders[name])
    return text


def redact_text(text: str, client_names: list[str] | None = None, enabled: bool | None = None) -> str:
    """脱敏手机号、身份证号、邮箱、银行卡号，以及调用方给出的客户企业名称。"""
    if text is None:
        return text
    if enabled is None:
        enabled = redaction_enabled()
    if not enabled or not text:
        return text

    names = configured_client_names() if client_names is None else client_names
    redacted = _redact_client_names(text, names)
    redacted = _EMAIL.sub("[邮箱]", redacted)
    redacted = _ID_CARD.sub("[身份证号]", redacted)
    redacted = _redact_bank_cards(redacted)
    redacted = _MOBILE_SPACED.sub("[手机号]", redacted)
    redacted = _MOBILE.sub("[手机号]", redacted)
    return redacted
