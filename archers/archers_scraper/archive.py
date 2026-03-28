from __future__ import annotations

import logging
import re
from pathlib import Path

from .config import ScraperConfig
from .models import CharacterRecord, LocationRecord, ScrapeResult
from .slugging import character_filename, ensure_unique_filename, location_filename
from .templates import infer_confidence_label, load_template, render_character_markdown, render_location_markdown


LOGGER = logging.getLogger(__name__)


SECTION_RE = re.compile(r"(?m)^## (.+?)\n")
LAST_UPDATED_RE = re.compile(r"(?m)^- \*\*Last updated:\*\* .*$")


def existing_markdown_files(directory: Path, index_name: str) -> set[str]:
    return {path.name for path in directory.glob("*.md") if path.name != index_name}


def choose_character_filename(record: CharacterRecord, existing: set[str], directory: Path) -> str:
    existing_match = find_existing_file_by_title(record.full_name, existing, directory)
    if existing_match:
        return existing_match
    candidate = character_filename(record.full_name, record.born)
    return ensure_unique_filename(candidate, existing, record.born)


def choose_location_filename(record: LocationRecord, existing: set[str], directory: Path) -> str:
    existing_match = find_existing_file_by_title(record.full_name, existing, directory)
    if existing_match:
        return existing_match
    candidate = location_filename(record.full_name)
    return ensure_unique_filename(candidate, existing)


def write_character(
    config: ScraperConfig,
    record: CharacterRecord,
    existing_files: set[str],
    update_existing: bool,
) -> ScrapeResult:
    template = load_template(config.character_template_path)
    record.filename = choose_character_filename(record, existing_files, config.characters_dir)
    path = config.characters_dir / record.filename
    confidence = infer_confidence_label(record)
    new_text = render_character_markdown(template, record, confidence)
    changed = _write_markdown(path, new_text, update_existing, config.dry_run)
    skipped_reason = None
    if path.exists() and not update_existing and not changed:
        skipped_reason = "exists"
    elif not changed:
        skipped_reason = "unchanged"
    return ScrapeResult("character", None, record, changed, path, skipped_reason=skipped_reason)  # type: ignore[arg-type]


def write_location(
    config: ScraperConfig,
    record: LocationRecord,
    existing_files: set[str],
    update_existing: bool,
) -> ScrapeResult:
    template = load_template(config.location_template_path)
    record.filename = choose_location_filename(record, existing_files, config.locations_dir)
    path = config.locations_dir / record.filename
    confidence = infer_confidence_label(record)
    new_text = render_location_markdown(template, record, confidence)
    changed = _write_markdown(path, new_text, update_existing, config.dry_run)
    skipped_reason = None
    if path.exists() and not update_existing and not changed:
        skipped_reason = "exists"
    elif not changed:
        skipped_reason = "unchanged"
    return ScrapeResult("location", None, record, changed, path, skipped_reason=skipped_reason)  # type: ignore[arg-type]


def _write_markdown(path: Path, new_text: str, update_existing: bool, dry_run: bool) -> bool:
    if path.exists():
        if not update_existing:
            LOGGER.info("Skipping existing file without --update-existing: %s", path.name)
            return False
        existing_text = path.read_text(encoding="utf-8")
        new_text = merge_with_existing(existing_text, new_text)
        if _should_preserve_existing(existing_text, new_text):
            LOGGER.info("Preserving richer existing content: %s", path.name)
            return False
        if _normalise_for_change_detection(existing_text) == _normalise_for_change_detection(new_text):
            return False
    if dry_run:
        LOGGER.info("Dry run: would write %s", path)
        return True
    path.write_text(new_text, encoding="utf-8")
    return True


def merge_with_existing(existing_text: str, generated_text: str) -> str:
    existing_sections = _extract_sections(existing_text)
    generated_sections = _extract_sections(generated_text)
    preserved = {
        heading: content
        for heading, content in existing_sections.items()
        if heading in {"Fun Facts", "Uncertain Details", "File Notes"} and _has_real_content(content)
    }
    generated_sections.update(preserved)
    title = generated_text.splitlines()[0]
    rebuilt = [title, ""]
    for heading, content in generated_sections.items():
        rebuilt.append(f"## {heading}")
        rebuilt.append(content.strip())
        rebuilt.append("")
    return "\n".join(rebuilt).rstrip() + "\n"


def _extract_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for idx, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections[heading] = text[start:end].strip()
    return sections


def _has_real_content(content: str) -> bool:
    stripped = "\n".join(line for line in content.splitlines() if line.strip())
    lowered = stripped.casefold()
    if lowered in {"", "-", "unknown", "unconfirmed", "- the archers", "the archers"}:
        return False
    if "only include facts that can be reasonably supported." in lowered:
        return False
    if "list anything not fully verified." in lowered:
        return False
    return True


def find_existing_file_by_title(title: str, existing: set[str], directory: Path) -> str | None:
    for filename in sorted(existing):
        path = directory / filename
        if not path.exists():
            continue
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0].strip()
        except (OSError, IndexError):
            continue
        if first_line == f"# {title}":
            return filename
    return None


def _normalise_for_change_detection(text: str) -> str:
    return LAST_UPDATED_RE.sub("- **Last updated:** __IGNORED__", text).strip()


def _should_preserve_existing(existing_text: str, new_text: str) -> bool:
    existing_score = _content_richness_score(existing_text)
    new_score = _content_richness_score(new_text)
    return existing_score > new_score


def _content_richness_score(text: str) -> int:
    score = 0
    lowered = text.casefold()
    penalised_phrases = [
        "a fuller source-backed overview still needs confirming",
        "no approved source yielded a fuller verified overview yet",
        "recent status not yet verified from an approved source",
        "no clearly supportable extra facts confirmed yet",
    ]
    for phrase in penalised_phrases:
        if phrase in lowered:
            score -= 2
    sections = _extract_sections(text)
    for heading, content in sections.items():
        cleaned = content.strip()
        if not cleaned or cleaned in {"- Unknown", "Unknown"}:
            continue
        if heading in {"Character Overview", "Location Overview", "Relationship Summary"}:
            score += 3
        elif heading in {"Partners / Spouses / Exes", "Children", "Who Currently Lives Here / Owns It", "Actor"}:
            score += 2
        else:
            score += 1
        if "Unknown" not in cleaned and "Unconfirmed" not in cleaned:
            score += 1
    return score
