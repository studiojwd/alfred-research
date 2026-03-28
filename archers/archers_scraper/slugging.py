from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


PUNCTUATION_RE = re.compile(r"[^a-z0-9\s-]")
WHITESPACE_RE = re.compile(r"[\s-]+")


def normalise_text(value: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    ascii_value = normalised.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.replace("&", " and ")
    return ascii_value.strip()


def slugify(value: str) -> str:
    value = normalise_text(value).lower()
    value = PUNCTUATION_RE.sub(" ", value)
    value = WHITESPACE_RE.sub("_", value)
    return value.strip("_")


def split_name(full_name: str) -> tuple[str, str]:
    cleaned = normalise_text(full_name)
    parts = [part for part in cleaned.split() if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    first_name = parts[0]
    surname = " ".join(parts[1:])
    return first_name, surname


def character_filename(full_name: str, birth_year: str | None = None) -> str:
    first_name, surname = split_name(full_name)
    if surname:
        base = f"{slugify(surname)}_{slugify(first_name)}"
    else:
        base = slugify(first_name)
    if birth_year:
        year_match = re.search(r"(18|19|20)\d{2}", birth_year)
        if year_match:
            base = f"{base}_{year_match.group(0)}"
    return f"{base}.md"


def location_filename(location_name: str) -> str:
    return f"{slugify(location_name)}.md"


def ensure_unique_filename(filename: str, existing: Iterable[str], birth_year: str | None = None) -> str:
    if filename not in existing:
        return filename
    stem = filename[:-3] if filename.endswith(".md") else filename
    suffix = ""
    if birth_year:
        match = re.search(r"(18|19|20)\d{2}", birth_year)
        if match and not stem.endswith(match.group(0)):
            suffix = f"_{match.group(0)}"
    candidate = f"{stem}{suffix}.md" if suffix else filename
    if candidate not in existing:
        return candidate
    counter = 2
    while True:
        candidate = f"{stem}{suffix}_{counter}.md"
        if candidate not in existing:
            return candidate
        counter += 1
