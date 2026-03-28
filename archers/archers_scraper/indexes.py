from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from .models import CharacterRecord, EntitySeed, LocationRecord


def _read_markdown_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in text.splitlines()]
    header_idx = next((idx for idx, line in enumerate(lines) if line.startswith("|")), None)
    if header_idx is None:
        return lines, []
    table_lines = [line for line in lines[header_idx:] if line.startswith("|")]
    if len(table_lines) < 2:
        return lines, []
    reader = csv.DictReader(io.StringIO("\n".join(table_lines)), delimiter="|")
    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned = {key.strip(): value.strip() for key, value in row.items() if key is not None and key.strip()}
        if cleaned and any(cleaned.values()):
            rows.append(cleaned)
    return lines[:header_idx], rows[1:]


def load_character_seeds(path: Path) -> list[EntitySeed]:
    _, rows = _read_markdown_table(path)
    seeds: list[EntitySeed] = []
    for row in rows:
        full_name = row.get("Full Name", "").strip()
        if not full_name:
            first_name = row.get("First Name", "")
            last_name = row.get("Last Name", "")
            full_name = " ".join(part for part in [first_name, last_name] if part).strip()
        if not full_name:
            continue
        common_name = row.get("Common Name", "").strip() or row.get("First Name", "").strip() or full_name
        notes = row.get("Family / Branch", "").strip() or row.get("Family / Connection", "").strip()
        seeds.append(
            EntitySeed(
                entity_type="character",
                full_name=full_name,
                common_name=common_name,
                notes=notes,
                raw_row=row,
            )
        )
    return seeds


def load_location_seeds(path: Path) -> list[EntitySeed]:
    _, rows = _read_markdown_table(path)
    seeds: list[EntitySeed] = []
    for row in rows:
        name = row.get("Location Name", "").strip()
        if not name:
            continue
        seeds.append(
            EntitySeed(
                entity_type="location",
                full_name=name,
                common_name=name,
                notes=row.get("Location Type", ""),
                raw_row=row,
            )
        )
    return seeds


def update_character_index(path: Path, records: list[CharacterRecord]) -> None:
    intro = [
        "# The Archers — character list",
        "",
        "| Full Name | Common Name | Born | First Introduced | Status | Family / Branch | File | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines = intro[:]
    for record in sorted(records, key=lambda item: item.full_name.lower()):
        lines.append(
            f"| {record.full_name} | {record.common_name or record.full_name} | {record.born} | "
            f"{record.first_introduced} | {record.status} | {record.family_branch} | "
            f"[{record.filename}]({record.filename}) | {'; '.join(record.file_notes) if record.file_notes else ''} |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def update_location_index(path: Path, records: list[LocationRecord]) -> None:
    intro = [
        "# The Archers — locations",
        "",
        "| Location Name | Type | Current Occupier / Owner | Status | File | Notes |",
        "|---|---|---|---|---|---|",
    ]
    lines = intro[:]
    for record in sorted(records, key=lambda item: item.full_name.lower()):
        current = "; ".join(record.current_occupier_owner) if record.current_occupier_owner else "Unknown"
        lines.append(
            f"| {record.full_name} | {record.location_type} | {current} | {record.status} | "
            f"[{record.filename}]({record.filename}) | {'; '.join(record.file_notes) if record.file_notes else ''} |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def collect_character_records_from_files(directory: Path, index_name: str) -> list[CharacterRecord]:
    records: list[CharacterRecord] = []
    for path in sorted(directory.glob("*.md")):
        if path.name == index_name:
            continue
        text = path.read_text(encoding="utf-8")
        title = _extract_heading(text)
        if not title:
            continue
        record = CharacterRecord(
            full_name=title,
            common_name=title.split()[0],
            born=_extract_bold_value(text, "Verified DOB") or "Unknown",
            first_introduced=_extract_bold_value(text, "Verified first appearance date or year") or "Unconfirmed",
            filename=path.name,
        )
        file_notes = _extract_bold_value(text, "Related files")
        if file_notes and file_notes != "None":
            record.related_files = [item.strip() for item in file_notes.split(",") if item.strip()]
        confidence = _extract_bold_value(text, "Confidence level")
        if confidence:
            record.file_notes.append(f"Confidence: {confidence}")
        records.append(record)
    return records


def collect_location_records_from_files(directory: Path, index_name: str) -> list[LocationRecord]:
    records: list[LocationRecord] = []
    for path in sorted(directory.glob("*.md")):
        if path.name == index_name:
            continue
        text = path.read_text(encoding="utf-8")
        title = _extract_heading(text)
        if not title:
            continue
        record = LocationRecord(
            full_name=title,
            location_type=_extract_section_line(text, "Location Type") or "Unknown",
            filename=path.name,
        )
        current = _extract_section_bullets(text, "Who Currently Lives Here / Owns It")
        if current:
            record.current_occupier_owner = current
        confidence = _extract_bold_value(text, "Confidence level")
        if confidence:
            record.file_notes.append(f"Confidence: {confidence}")
        records.append(record)
    return records


def _extract_heading(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_bold_value(text: str, label: str) -> str:
    pattern = re.compile(rf"\*\*{re.escape(label)}:\*\*\s*(.+)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _extract_section_line(text: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\n(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _extract_section_bullets(text: str, heading: str) -> list[str]:
    pattern = re.compile(rf"^## {re.escape(heading)}\n(.*?)(?:\n## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(text)
    if not match:
        return []
    bullets = []
    for line in match.group(1).splitlines():
        if line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets
