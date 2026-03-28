from __future__ import annotations

from datetime import date
from pathlib import Path

from .models import CharacterRecord, LocationRecord


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def render_bullets(items: list[str], fallback: str = "Unknown") -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    if not cleaned:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in cleaned)


def render_character_markdown(template: str, record: CharacterRecord, confidence_label: str) -> str:
    _ = template
    overview = _normalise_prose(record.overview)
    work_role = _normalise_prose(record.work_role)
    relationship_summary = _normalise_prose(record.relationship_summary)
    lines = [
        f"# {record.full_name}",
        "",
        "## Character Overview",
        overview,
        "",
        "## DOB",
        f"- **Verified DOB:** {record.born}",
        "",
        "## First Introduced",
        f"- **Verified first appearance date or year:** {record.first_introduced}",
        "",
        "## Where They Live Now",
        record.where_they_live_now,
        "",
        "## Parents",
        render_bullets(record.parents),
        "",
        "## Siblings",
        render_bullets(record.siblings),
        "",
        "## Partners / Spouses / Exes",
        render_bullets(record.partners),
        "",
        "## Children",
        render_bullets(record.children),
        "",
        "## Work / Role",
        work_role,
        "",
        "## Relationship Summary",
        relationship_summary,
        "",
        "## Key Storylines / Timeline",
        "",
        "### Early life",
        render_bullets(record.timeline_early_life),
        "",
        "### Major adult storylines",
        render_bullets(record.timeline_major_storylines),
        "",
        "### Recent position",
        render_bullets(record.timeline_recent_position),
        "",
        "## Fun Facts",
        render_bullets(record.fun_facts),
        "",
        "## Actor",
        "",
        "### Current actor",
        render_bullets([record.actor_current]),
        "",
        "### Past actors",
        render_bullets(record.actor_past),
        "",
        "## Uncertain Details",
        render_bullets(record.uncertain_details),
        "",
        "## File Notes",
        f"- **Last updated:** {date.today().isoformat()}",
        f"- **Confidence level:** {confidence_label}",
        f"- **Related files:** {', '.join(record.related_files) if record.related_files else 'None'}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def render_location_markdown(template: str, record: LocationRecord, confidence_label: str) -> str:
    _ = template
    overview = _normalise_prose(record.overview)
    lines = [
        f"# {record.full_name}",
        "",
        "## Location Type",
        record.location_type,
        "",
        "## Location Overview",
        overview,
        "",
        "## Who Currently Lives Here / Owns It",
        render_bullets(record.current_occupier_owner, fallback="Not applicable"),
        "",
        "## Who Lived Here / Owned It In The Past",
        render_bullets(record.past_occupier_owner),
        "",
        "## Key Storylines That Happened Here",
        "",
        "### Early notable events",
        render_bullets(record.storylines_early),
        "",
        "### Major storylines",
        render_bullets(record.storylines_major),
        "",
        "### Recent significance",
        render_bullets(record.storylines_recent),
        "",
        "## Related Characters",
        render_bullets(record.related_characters),
        "",
        "## Uncertain Details",
        render_bullets(record.uncertain_details),
        "",
        "## File Notes",
        f"- **Last updated:** {date.today().isoformat()}",
        f"- **Confidence level:** {confidence_label}",
        f"- **Related files:** {', '.join(record.related_files) if record.related_files else 'None'}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def infer_confidence_label(record: CharacterRecord | LocationRecord) -> str:
    source_log = getattr(record, "source_log", {})
    if not source_log:
        return "Low"
    average = sum(field.confidence for field in source_log.values()) / len(source_log)
    if average >= 0.8:
        return "High"
    if average >= 0.55:
        return "Medium"
    return "Low"


def _normalise_prose(text: str) -> str:
    cleaned = " ".join(text.split())
    if cleaned in {"Unknown", "Unconfirmed."}:
        return cleaned
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned
