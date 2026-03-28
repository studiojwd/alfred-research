from __future__ import annotations

import logging
from pathlib import Path

from .archive import existing_markdown_files, write_character, write_location
from .config import ScraperConfig
from .family_tree import find_family_tree_file, update_family_tree
from .indexes import (
    collect_character_records_from_files,
    collect_location_records_from_files,
    load_character_seeds,
    load_location_seeds,
    update_character_index,
    update_location_index,
)
from .llm_enrichment import OpenAIEnricher, apply_character_enrichment, apply_location_enrichment
from .merge import merge_character, merge_location
from .models import CharacterRecord, EntitySeed, LocationRecord
from .sources import OfficialArchersAdapter, RadioTimesAdapter, ReferenceWikiAdapter, UmraAdapter, WikipediaAdapter


LOGGER = logging.getLogger(__name__)


def build_adapters(config: ScraperConfig):
    adapters = {
        "official": OfficialArchersAdapter(config),
        "radiotimes": RadioTimesAdapter(config),
        "wikipedia": WikipediaAdapter(config),
        "thearcherswiki": ReferenceWikiAdapter(config),
        "umra": UmraAdapter(config),
    }
    ordered: list = []
    for source in sorted(config.source_priority, key=lambda item: item.priority):
        if source.enabled and source.name in adapters:
            ordered.append(adapters[source.name])
    return ordered


def run_character_pipeline(config: ScraperConfig, target_name: str | None = None) -> list[CharacterRecord]:
    seeds = load_character_seeds(config.character_index_path)
    seeds = _filter_seeds(seeds, target_name, entity_type="character")
    adapters = build_adapters(config)
    existing = existing_markdown_files(config.characters_dir, config.character_index_path.name)
    enricher = OpenAIEnricher(config)
    records: list[CharacterRecord] = []
    processed = 0
    written = 0
    skipped_existing = 0
    unchanged = 0
    no_source_match = 0
    matched_source_pages = 0
    for seed in dedupe_seeds(seeds):
        processed += 1
        path = config.characters_dir / write_safe_candidate_name(seed.full_name)
        if config.create_missing_only and any(file.startswith(path.stem) for file in existing):
            LOGGER.info("Skipping existing character in create-missing-only mode: %s", seed.full_name)
            skipped_existing += 1
            continue
        documents = [document for adapter in adapters for document in adapter.fetch(seed)]
        if not documents:
            LOGGER.info("No approved source page matched character: %s", seed.full_name)
            no_source_match += 1
        else:
            matched_source_pages += 1
        record = merge_character(seed, documents)
        apply_character_enrichment(record, enricher.enrich_character(seed, record, documents))
        result = write_character(config, record, existing, update_existing=config.update_existing)
        existing.add(record.filename)
        if result.changed:
            written += 1
            LOGGER.info("Wrote character file: %s", result.path.name)
        elif result.skipped_reason == "exists":
            skipped_existing += 1
            LOGGER.info("Skipped existing character file: %s", result.path.name)
        else:
            unchanged += 1
            LOGGER.info("No content change for character file: %s", result.path.name)
        records.append(record)
    if target_name is None:
        update_character_index(
            config.character_index_path,
            collect_character_records_from_files(config.characters_dir, config.character_index_path.name),
        )
        _update_family_tree_if_present(config, collect_character_records_from_files(config.characters_dir, config.character_index_path.name))
    _append_research_log(config, records, [])
    LOGGER.info(
        "Character run summary: processed=%s written=%s skipped_existing=%s unchanged=%s matched_source_pages=%s no_source_match=%s",
        processed,
        written,
        skipped_existing,
        unchanged,
        matched_source_pages,
        no_source_match,
    )
    return records


def run_location_pipeline(config: ScraperConfig, target_name: str | None = None) -> list[LocationRecord]:
    seeds = load_location_seeds(config.location_index_path)
    seeds = _filter_seeds(seeds, target_name, entity_type="location")
    adapters = build_adapters(config)
    existing = existing_markdown_files(config.locations_dir, config.location_index_path.name)
    enricher = OpenAIEnricher(config)
    records: list[LocationRecord] = []
    processed = 0
    written = 0
    skipped_existing = 0
    unchanged = 0
    no_source_match = 0
    matched_source_pages = 0
    for seed in dedupe_seeds(seeds):
        processed += 1
        path = config.locations_dir / write_safe_candidate_name(seed.full_name)
        if config.create_missing_only and any(file.startswith(path.stem) for file in existing):
            LOGGER.info("Skipping existing location in create-missing-only mode: %s", seed.full_name)
            skipped_existing += 1
            continue
        documents = [document for adapter in adapters for document in adapter.fetch(seed)]
        if not documents:
            LOGGER.info("No approved source page matched location: %s", seed.full_name)
            no_source_match += 1
        else:
            matched_source_pages += 1
        record = merge_location(seed, documents)
        apply_location_enrichment(record, enricher.enrich_location(seed, record, documents))
        result = write_location(config, record, existing, update_existing=config.update_existing)
        existing.add(record.filename)
        if result.changed:
            written += 1
            LOGGER.info("Wrote location file: %s", result.path.name)
        elif result.skipped_reason == "exists":
            skipped_existing += 1
            LOGGER.info("Skipped existing location file: %s", result.path.name)
        else:
            unchanged += 1
            LOGGER.info("No content change for location file: %s", result.path.name)
        records.append(record)
    if target_name is None:
        update_location_index(
            config.location_index_path,
            collect_location_records_from_files(config.locations_dir, config.location_index_path.name),
        )
    _append_research_log(config, [], records)
    LOGGER.info(
        "Location run summary: processed=%s written=%s skipped_existing=%s unchanged=%s matched_source_pages=%s no_source_match=%s",
        processed,
        written,
        skipped_existing,
        unchanged,
        matched_source_pages,
        no_source_match,
    )
    return records


def dedupe_seeds(seeds: list[EntitySeed]) -> list[EntitySeed]:
    deduped: dict[tuple[str, str], EntitySeed] = {}
    for seed in seeds:
        key = (seed.entity_type, seed.full_name.casefold())
        if key not in deduped:
            deduped[key] = seed
            continue
        if seed.notes and len(seed.notes) > len(deduped[key].notes):
            deduped[key] = seed
    return list(deduped.values())


def write_safe_candidate_name(name: str) -> str:
    from .slugging import slugify

    return slugify(name)


def _filter_seeds(seeds: list[EntitySeed], target_name: str | None, entity_type: str) -> list[EntitySeed]:
    if not target_name:
        return seeds
    target = target_name.casefold()
    matched = [seed for seed in seeds if seed.full_name.casefold() == target or seed.common_name.casefold() == target]
    if matched:
        return matched
    return [
        EntitySeed(
            entity_type=entity_type,  # type: ignore[arg-type]
            full_name=target_name,
            common_name=target_name.split()[0].strip(),
            notes="",
            raw_row={},
        )
    ]


def _append_research_log(
    config: ScraperConfig,
    characters: list[CharacterRecord],
    locations: list[LocationRecord],
) -> None:
    lines = ["# Research Notes", ""]
    for record in characters:
        lines.append(f"## {record.full_name}")
        for field_name, field_value in sorted(record.source_log.items()):
            evidence = field_value.evidence[0]
            lines.append(f"- `{field_name}`: {field_value.value} ({evidence.source_name}, confidence {field_value.confidence:.2f})")
            lines.append(f"  Source: {evidence.source_url}")
        lines.append("")
    for record in locations:
        lines.append(f"## {record.full_name}")
        for field_name, field_value in sorted(record.source_log.items()):
            evidence = field_value.evidence[0]
            lines.append(f"- `{field_name}`: {field_value.value} ({evidence.source_name}, confidence {field_value.confidence:.2f})")
            lines.append(f"  Source: {evidence.source_url}")
        lines.append("")
    payload = "\n".join(lines).rstrip() + "\n"
    if config.dry_run:
        LOGGER.info("Dry run: would update %s", config.research_log_path)
        return
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    config.research_log_path.write_text(payload, encoding="utf-8")


def _update_family_tree_if_present(config: ScraperConfig, records: list[CharacterRecord]) -> None:
    family_tree_path = find_family_tree_file(config.root)
    if family_tree_path is None:
        return
    update_family_tree(family_tree_path, records, config.dry_run)
