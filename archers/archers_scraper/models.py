from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


EntityType = Literal["character", "location"]


@dataclass(slots=True)
class SourceEvidence:
    source_name: str
    source_url: str
    confidence: float
    notes: str = ""


@dataclass(slots=True)
class FieldValue:
    value: str
    confidence: float
    evidence: list[SourceEvidence] = field(default_factory=list)


@dataclass(slots=True)
class EntitySeed:
    entity_type: EntityType
    full_name: str
    common_name: str
    notes: str = ""
    raw_row: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class CharacterRecord:
    full_name: str
    common_name: str = ""
    born: str = "Unknown"
    first_introduced: str = "Unconfirmed"
    status: str = "Unknown"
    family_branch: str = "Unknown"
    overview: str = "Unknown"
    where_they_live_now: str = "Unknown"
    parents: list[str] = field(default_factory=list)
    siblings: list[str] = field(default_factory=list)
    partners: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    work_role: str = "Unknown"
    relationship_summary: str = "Unknown"
    timeline_early_life: list[str] = field(default_factory=list)
    timeline_major_storylines: list[str] = field(default_factory=list)
    timeline_recent_position: list[str] = field(default_factory=list)
    fun_facts: list[str] = field(default_factory=list)
    actor_current: str = "Unknown"
    actor_past: list[str] = field(default_factory=list)
    uncertain_details: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)
    source_log: dict[str, FieldValue] = field(default_factory=dict)
    file_notes: list[str] = field(default_factory=list)
    filename: str = ""


@dataclass(slots=True)
class LocationRecord:
    full_name: str
    location_type: str = "Unknown"
    status: str = "Unknown"
    overview: str = "Unknown"
    current_occupier_owner: list[str] = field(default_factory=list)
    past_occupier_owner: list[str] = field(default_factory=list)
    storylines_early: list[str] = field(default_factory=list)
    storylines_major: list[str] = field(default_factory=list)
    storylines_recent: list[str] = field(default_factory=list)
    related_characters: list[str] = field(default_factory=list)
    uncertain_details: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)
    source_log: dict[str, FieldValue] = field(default_factory=dict)
    file_notes: list[str] = field(default_factory=list)
    filename: str = ""


@dataclass(slots=True)
class ScrapeResult:
    entity_type: EntityType
    seed: EntitySeed
    record: CharacterRecord | LocationRecord
    changed: bool
    path: Path
    skipped_reason: str | None = None


@dataclass(slots=True)
class SourceDocument:
    source_name: str
    source_url: str
    entity_name: str
    payload: dict[str, str | list[str]]
    confidence: float
    notes: list[str] = field(default_factory=list)
