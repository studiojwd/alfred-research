from __future__ import annotations

import re

from .models import CharacterRecord, EntitySeed, FieldValue, LocationRecord, SourceDocument, SourceEvidence


CHARACTER_FIELD_MAP = {
    "overview": "overview",
    "born": "born",
    "first_introduced": "first_introduced",
    "where_they_live_now": "where_they_live_now",
    "work_role": "work_role",
    "actor_current": "actor_current",
}

LOCATION_FIELD_MAP = {
    "location_type": "location_type",
    "location_overview": "overview",
}

GENERIC_VALUES = {
    "tv guide",
    "radio times",
    "wikipedia",
    "search",
    "unknown",
    "unconfirmed",
    "on tv now",
    "the archers",
}


def merge_character(seed: EntitySeed, documents: list[SourceDocument]) -> CharacterRecord:
    record = CharacterRecord(
        full_name=seed.full_name,
        common_name=seed.common_name,
        family_branch=seed.notes or "Unknown",
    )
    for document in sorted(documents, key=lambda item: (-item.confidence, item.source_name)):
        for source_key, target_field in CHARACTER_FIELD_MAP.items():
            raw_value = document.payload.get(source_key)
            if not raw_value:
                continue
            cleaned_value = _coerce_text(raw_value)
            if not _is_meaningful_value(cleaned_value, seed.full_name):
                continue
            if getattr(record, target_field) in {"Unknown", "Unconfirmed", ""}:
                setattr(record, target_field, cleaned_value)
                record.source_log[target_field] = _field_value(document, cleaned_value)
        fun_facts = document.payload.get("fun_facts")
        if isinstance(fun_facts, list):
            for item in fun_facts:
                if _is_meaningful_value(item, seed.full_name) and item not in record.fun_facts:
                    record.fun_facts.append(item)
        actor_past = document.payload.get("actor_past")
        if isinstance(actor_past, list):
            for item in actor_past:
                if _is_meaningful_value(item, seed.full_name) and item not in record.actor_past:
                    record.actor_past.append(item)
        partners = document.payload.get("partners")
        if isinstance(partners, list):
            for item in partners:
                if _is_meaningful_value(item, seed.full_name) and item not in record.partners:
                    record.partners.append(item)
        children = document.payload.get("children")
        if isinstance(children, list):
            for item in children:
                if _is_meaningful_value(item, seed.full_name) and item not in record.children:
                    record.children.append(item)
    if not record.overview or record.overview == "Unknown":
        record.overview = (
            f"{seed.full_name} is an Archers character listed in the project index. "
            "A fuller source-backed overview still needs confirming."
        )
        record.uncertain_details.append("No approved source yielded a fuller verified overview yet.")
    if not record.relationship_summary or record.relationship_summary == "Unknown":
        record.relationship_summary = _build_relationship_summary(record, seed)
    _enrich_character_from_overview(record)
    if not record.timeline_recent_position:
        record.timeline_recent_position.append("Recent status not yet verified from an approved source.")
    if not record.fun_facts:
        record.fun_facts.append("No clearly supportable extra facts confirmed yet.")
    if not record.actor_past:
        record.actor_past.append("Unknown")
    if not record.uncertain_details:
        record.uncertain_details.append("This file still needs source-backed detail in several sections.")
    return record


def merge_location(seed: EntitySeed, documents: list[SourceDocument]) -> LocationRecord:
    record = LocationRecord(full_name=seed.full_name, location_type=seed.notes or "Unknown")
    for document in sorted(documents, key=lambda item: (-item.confidence, item.source_name)):
        for source_key, target_field in LOCATION_FIELD_MAP.items():
            raw_value = document.payload.get(source_key)
            if not raw_value:
                continue
            cleaned_value = _coerce_text(raw_value)
            if not _is_meaningful_value(cleaned_value, seed.full_name):
                continue
            current = getattr(record, target_field)
            if current in {"Unknown", "Unconfirmed", ""}:
                setattr(record, target_field, cleaned_value)
                record.source_log[target_field] = _field_value(document, cleaned_value)
        current_people = document.payload.get("current_occupier_owner")
        if isinstance(current_people, list):
            for item in current_people:
                if _is_meaningful_value(item, seed.full_name) and item not in record.current_occupier_owner:
                    record.current_occupier_owner.append(item)
    if not record.overview or record.overview == "Unknown":
        record.overview = f"{seed.full_name} is a named Archers location from the project index. Further source work is still required."
        record.uncertain_details.append("No approved source yielded a fuller verified location summary yet.")
    if not record.storylines_recent:
        record.storylines_recent.append("Recent significance not yet verified from an approved source.")
    return record


def _coerce_text(value: str | list[str]) -> str:
    if isinstance(value, list):
        return "; ".join(item.strip() for item in value if item.strip()) or "Unknown"
    return value.strip() or "Unknown"


def _field_value(document: SourceDocument, value: str) -> FieldValue:
    return FieldValue(
        value=value,
        confidence=document.confidence,
        evidence=[
            SourceEvidence(
                source_name=document.source_name,
                source_url=document.source_url,
                confidence=document.confidence,
                notes="; ".join(document.notes),
            )
        ],
    )


def _is_meaningful_value(value: str, entity_name: str) -> bool:
    lowered = value.strip().casefold()
    if not lowered or lowered in GENERIC_VALUES:
        return False
    if lowered.startswith("on tv"):
        return False
    if lowered in {"none", "n/a", "na"}:
        return False
    if lowered == entity_name.casefold():
        return False
    if len(lowered) < 4:
        return False
    return True


def _build_relationship_summary(record: CharacterRecord, seed: EntitySeed) -> str:
    parts: list[str] = []
    surname = seed.full_name.split()[-1] if seed.full_name.split() else seed.full_name
    if surname:
        parts.append(f"{record.full_name} is part of the {surname} family line in The Archers.")
    if record.partners and record.partners != ["Unknown"]:
        partners = ", ".join(record.partners)
        parts.append(f"Known partner links include {partners}.")
    if record.children and record.children != ["Unknown"]:
        children = ", ".join(record.children)
        parts.append(f"Known children include {children}.")
    if seed.notes and seed.notes.strip().casefold() not in {"unknown", "unconfirmed"}:
        cleaned_notes = seed.notes.strip().rstrip(".")
        parts.append(cleaned_notes[0].upper() + cleaned_notes[1:] + ".")
    if not parts:
        return "Unconfirmed."
    summary = " ".join(parts)
    summary = re.sub(r"\s{2,}", " ", summary).strip()
    return summary


ROLE_PATTERNS = [
    (r"\bfarmer\b", "Farmer"),
    (r"\borganic farmer\b", "Organic farmer"),
    (r"\bpub landlord\b|\bpub landlady\b|\blandlord\b|\blandlady\b", "Pub landlord"),
    (r"\bsolicitor\b", "Solicitor"),
    (r"\bdoctor\b|\bgp\b", "Doctor"),
    (r"\bvicar\b", "Vicar"),
    (r"\bhotelier\b|\bhotel manager\b", "Hotel manager"),
    (r"\bvet\b|\bveterinary\b", "Vet"),
    (r"\bbusinessman\b|\bbusinesswoman\b", "Businessperson"),
]


def _enrich_character_from_overview(record: CharacterRecord) -> None:
    overview = record.overview
    if overview in {"Unknown", ""}:
        return
    if record.children == [] or record.children == ["Unknown"]:
        children = _extract_children_from_overview(overview)
        if children:
            record.children = children
    if record.work_role == "Unknown":
        role = _extract_role_from_overview(overview)
        if role:
            record.work_role = role
    if record.where_they_live_now == "Unknown":
        home = _extract_home_from_overview(overview)
        if home:
            record.where_they_live_now = home
    record.overview = _compress_overview(overview, record.full_name)


def _extract_children_from_overview(text: str) -> list[str]:
    patterns = [
        r"\bthey have (?:three|four|five|several|\w+) children:\s*([A-Z][^.]+)",
        r"\bhas (?:three|four|five|several|\w+) children:\s*([A-Z][^.]+)",
        r"\bchildren(?: include| are)?\s*:\s*([A-Z][^.]+)",
        r"\btheir children are\s*([A-Z][^.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        tail = match.group(1)
        tail = re.sub(r"\([^)]*\)", "", tail)
        parts = re.split(r",|\band\b", tail)
        cleaned = [part.strip(" .") for part in parts if part.strip(" .")]
        if cleaned:
            return cleaned
    return []


def _extract_role_from_overview(text: str) -> str:
    specific = re.search(r"\bis an? ([^.]*?\bfarmer\b(?: at [A-Z][A-Za-z' -]+)?)", text, re.IGNORECASE)
    if specific:
        role = specific.group(1).strip(" .")
        role = re.split(r"\band\b|\bwho\b|\bwith\b|\blives\b", role, maxsplit=1)[0].strip(" .,")
        role = re.sub(r"\s{2,}", " ", role)
        return role[0].upper() + role[1:]
    named_role = re.search(
        r"\bis an? (solicitor|doctor|gp|vicar|vet|hotel manager|businessman|businesswoman)\b",
        text,
        re.IGNORECASE,
    )
    if named_role:
        role = named_role.group(1).strip().lower()
        role_map = {
            "gp": "Doctor",
            "businessman": "Businessperson",
            "businesswoman": "Businessperson",
        }
        return role_map.get(role, role.title())
    lowered = text.casefold()
    for pattern, label in ROLE_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            return label
    return ""


def _extract_home_from_overview(text: str) -> str:
    patterns = [
        r"\blives at ([A-Z][A-Za-z' -]+)",
        r"\blives in ([A-Z][A-Za-z' -]+)",
        r"\bresident of ([A-Z][A-Za-z' -]+)",
        r"\bhome at ([A-Z][A-Za-z' -]+)",
        r"\bresident in ([A-Z][A-Za-z' -]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        home = match.group(1).strip(" .")
        home = re.split(r"\bwith\b|\band\b|\bwhere\b", home)[0].strip(" .,")
        if len(home) >= 3:
            return home
    return ""


def _compress_overview(text: str, full_name: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        lowered = sentence.casefold()
        if "[ " in sentence or "dead ringers" in lowered:
            continue
        if "writers for the show paired" in lowered:
            continue
        kept.append(sentence)
        if len(kept) == 3:
            break
    if not kept:
        return text
    compressed = " ".join(kept)
    compressed = re.sub(r"\s{2,}", " ", compressed).strip()
    if full_name.casefold() not in compressed.casefold():
        return text
    return compressed
