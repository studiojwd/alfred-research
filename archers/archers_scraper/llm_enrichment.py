from __future__ import annotations

import json
import logging
import os
from typing import Any

from .config import ScraperConfig
from .models import CharacterRecord, EntitySeed, LocationRecord, SourceDocument


LOGGER = logging.getLogger(__name__)


CHARACTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overview": {"type": "string"},
        "work_role": {"type": "string"},
        "where_they_live_now": {"type": "string"},
        "relationship_summary": {"type": "string"},
        "children": {"type": "array", "items": {"type": "string"}},
        "partners": {"type": "array", "items": {"type": "string"}},
        "uncertain_details": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overview",
        "work_role",
        "where_they_live_now",
        "relationship_summary",
        "children",
        "partners",
        "uncertain_details",
    ],
}


LOCATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "overview": {"type": "string"},
        "location_type": {"type": "string"},
        "current_occupier_owner": {"type": "array", "items": {"type": "string"}},
        "related_characters": {"type": "array", "items": {"type": "string"}},
        "uncertain_details": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "overview",
        "location_type",
        "current_occupier_owner",
        "related_characters",
        "uncertain_details",
    ],
}


class OpenAIEnricher:
    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self._client = None

    def available(self) -> bool:
        if not self.config.use_llm:
            return False
        if not os.environ.get("OPENAI_API_KEY"):
            LOGGER.warning("LLM enrichment requested but OPENAI_API_KEY is not set")
            return False
        try:
            from openai import OpenAI
        except ImportError:
            LOGGER.warning("LLM enrichment requested but the openai package is not installed")
            return False
        if self._client is None:
            self._client = OpenAI()
        return True

    def enrich_character(
        self,
        seed: EntitySeed,
        record: CharacterRecord,
        documents: list[SourceDocument],
    ) -> dict[str, Any] | None:
        if not self.available() or not documents:
            return None
        prompt = self._character_prompt(seed, record, documents)
        return self._request_json(prompt, CHARACTER_SCHEMA, "archers_character_enrichment")

    def enrich_location(
        self,
        seed: EntitySeed,
        record: LocationRecord,
        documents: list[SourceDocument],
    ) -> dict[str, Any] | None:
        if not self.available() or not documents:
            return None
        prompt = self._location_prompt(seed, record, documents)
        return self._request_json(prompt, LOCATION_SCHEMA, "archers_location_enrichment")

    def _request_json(self, prompt: str, schema: dict[str, Any], schema_name: str) -> dict[str, Any] | None:
        try:
            response = self._client.responses.create(
                model=self.config.llm_model,
                instructions=(
                    "You are editing a British English encyclopedia about The Archers. "
                    "Only use the supplied source snippets. Do not invent or guess. "
                    "If a field is not supported, return 'Unknown' or an empty list as appropriate."
                ),
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
            )
        except Exception as exc:
            LOGGER.warning("LLM enrichment failed: %s", exc)
            return None
        try:
            return json.loads(response.output_text)
        except Exception as exc:
            LOGGER.warning("LLM enrichment returned non-JSON output: %s", exc)
            return None

    def _character_prompt(
        self,
        seed: EntitySeed,
        record: CharacterRecord,
        documents: list[SourceDocument],
    ) -> str:
        snippets = self._format_documents(documents)
        return (
            f"Character: {seed.full_name}\n"
            f"Existing overview: {record.overview}\n"
            f"Existing first introduced: {record.first_introduced}\n"
            f"Existing partners: {', '.join(record.partners) if record.partners else 'Unknown'}\n\n"
            "Source snippets:\n"
            f"{snippets}\n\n"
            "Return concise British English field values. "
            "Prefer one or two sentence summaries. "
            "Use only supported facts from the snippets."
        )

    def _location_prompt(
        self,
        seed: EntitySeed,
        record: LocationRecord,
        documents: list[SourceDocument],
    ) -> str:
        snippets = self._format_documents(documents)
        return (
            f"Location: {seed.full_name}\n"
            f"Existing overview: {record.overview}\n"
            f"Existing type: {record.location_type}\n\n"
            "Source snippets:\n"
            f"{snippets}\n\n"
            "Return concise British English field values. "
            "Use only supported facts from the snippets."
        )

    def _format_documents(self, documents: list[SourceDocument]) -> str:
        blocks: list[str] = []
        for idx, document in enumerate(documents[:4], start=1):
            payload_lines = []
            for key, value in document.payload.items():
                payload_lines.append(f"{key}: {value}")
            blocks.append(
                f"[Source {idx}] {document.source_name} | {document.source_url}\n" + "\n".join(payload_lines)
            )
        return "\n\n".join(blocks)


def apply_character_enrichment(record: CharacterRecord, payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    if payload.get("overview") and record.overview.startswith(record.full_name):
        record.overview = payload["overview"]
    if payload.get("work_role") and record.work_role == "Unknown" and payload["work_role"] != "Unknown":
        record.work_role = payload["work_role"]
    if payload.get("where_they_live_now") and record.where_they_live_now == "Unknown" and payload["where_they_live_now"] != "Unknown":
        record.where_they_live_now = payload["where_they_live_now"]
    has_structured_relationships = (
        any(item != "Unknown" for item in record.partners)
        or any(item != "Unknown" for item in record.children)
    )
    if (
        payload.get("relationship_summary")
        and payload["relationship_summary"] != "Unknown"
        and not has_structured_relationships
    ):
        record.relationship_summary = payload["relationship_summary"]
    for field in ["children", "partners", "uncertain_details"]:
        values = payload.get(field) or []
        if isinstance(values, list):
            existing = getattr(record, field)
            for item in values:
                if item and item not in existing and item != "Unknown":
                    existing.append(item)


def apply_location_enrichment(record: LocationRecord, payload: dict[str, Any] | None) -> None:
    if not payload:
        return
    if payload.get("overview") and record.overview.startswith(record.full_name):
        record.overview = payload["overview"]
    if payload.get("location_type") and record.location_type == "Unknown" and payload["location_type"] != "Unknown":
        record.location_type = payload["location_type"]
    for field in ["current_occupier_owner", "related_characters", "uncertain_details"]:
        values = payload.get(field) or []
        if isinstance(values, list):
            existing = getattr(record, field)
            for item in values:
                if item and item not in existing and item != "Unknown":
                    existing.append(item)
