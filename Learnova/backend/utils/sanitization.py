import re
from typing import Any, Iterable, Optional


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HTML_TAG_RE = re.compile(r"<[^>]*>")
_DANGEROUS_SCHEME_RE = re.compile(r"(?i)\b(?:javascript|data|vbscript)\s*:")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_single_line(value: Any, *, max_length: Optional[int] = None) -> Any:
    """Clean short user-entered text without touching non-string values."""
    if value is None or not isinstance(value, str):
        return value

    text = _CONTROL_CHARS_RE.sub("", value)
    text = _HTML_TAG_RE.sub("", text)
    text = _DANGEROUS_SCHEME_RE.sub("", text)
    text = text.replace("<", "").replace(">", "")
    text = _WHITESPACE_RE.sub(" ", text).strip()

    if max_length is not None:
        text = text[:max_length].strip()

    return text


def sanitize_multiline_text(value: Any, *, max_length: Optional[int] = None) -> Any:
    """Remove invisible control characters from long pasted text content."""
    if value is None or not isinstance(value, str):
        return value

    text = _CONTROL_CHARS_RE.sub("", value)
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    if max_length is not None:
        text = text[:max_length].strip()

    return text


def sanitize_digits(value: Any, *, max_length: Optional[int] = None) -> Any:
    """Keep only decimal digits for numeric text fields such as phone/card tails."""
    if value is None or not isinstance(value, str):
        return value

    digits = "".join(ch for ch in value if ch.isdigit())
    if max_length is not None:
        digits = digits[:max_length]
    return digits


def sanitize_choice(value: Any, allowed: Iterable[str]) -> Optional[str]:
    """Sanitize a short enum-like input and return it only when allowed."""
    cleaned = sanitize_single_line(value, max_length=64)
    if not isinstance(cleaned, str):
        return None

    cleaned = cleaned.lower()
    return cleaned if cleaned in set(allowed) else None


def sanitize_answer_indices(value: Any, *, max_answers: int = 100) -> list[int]:
    """Return a bounded list of non-negative answer indexes from request input."""
    if not isinstance(value, list):
        return []

    answers: list[int] = []
    for item in value[:max_answers]:
        if isinstance(item, bool):
            continue
        if isinstance(item, int) and item >= 0:
            answers.append(item)

    return answers
