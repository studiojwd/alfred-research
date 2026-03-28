from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import ScraperConfig, default_source_priority
from .orchestrator import run_character_pipeline, run_location_pipeline


def _parse_sources(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {item.strip() for item in raw_value.split(",") if item.strip()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape and update the Archers encyclopedia archive.")
    scope = parser.add_mutually_exclusive_group(required=False)
    scope.add_argument("--characters", action="store_true", help="Process characters only.")
    scope.add_argument("--locations", action="store_true", help="Process locations only.")
    scope.add_argument("--all", action="store_true", help="Process characters and locations.")
    parser.add_argument("--character", help='Process one character, for example "Jill Archer".')
    parser.add_argument("--location", help='Process one location, for example "Brookfield Farm".')
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files.")
    parser.add_argument("--update-existing", action="store_true", help="Update files that already exist.")
    parser.add_argument("--create-missing-only", action="store_true", help="Only create missing files.")
    parser.add_argument("--use-llm", action="store_true", help="Use an LLM to synthesise fields from fetched source snippets.")
    parser.add_argument("--llm-model", default="gpt-4o-mini", help="OpenAI model name for optional LLM enrichment.")
    parser.add_argument("--research-mode", action="store_true", help="Alias for enabling LLM-assisted enrichment on matched pages.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count for transient HTTP failures.")
    parser.add_argument(
        "--max-source-failures",
        type=int,
        default=3,
        help="Disable a source for the current run after this many consecutive failures.",
    )
    parser.add_argument(
        "--sources",
        help="Comma-separated source keys to use. Available: official,radiotimes,wikipedia,thearcherswiki,umra",
    )
    parser.add_argument(
        "--skip-sources",
        help="Comma-separated source keys to skip. Available: official,radiotimes,wikipedia,thearcherswiki,umra",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root. Defaults to the current directory.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(name)s: %(message)s")
    source_priority = default_source_priority()
    requested_sources = _parse_sources(args.sources)
    skipped_sources = _parse_sources(args.skip_sources)
    if requested_sources:
        for source in source_priority:
            source.enabled = source.name in requested_sources
    if skipped_sources:
        for source in source_priority:
            if source.name in skipped_sources:
                source.enabled = False
    config = ScraperConfig(
        root=args.root.resolve(),
        dry_run=args.dry_run,
        update_existing=args.update_existing,
        create_missing_only=args.create_missing_only,
        use_llm=args.use_llm or args.research_mode,
        llm_model=args.llm_model,
        research_mode=args.research_mode,
        timeout_seconds=args.timeout,
        retries=args.retries,
        max_source_failures=args.max_source_failures,
        source_priority=source_priority,
    )
    run_all = args.all or not any([args.characters, args.locations, args.character, args.location])
    if args.characters or args.character or run_all:
        run_character_pipeline(config, target_name=args.character)
    if args.locations or args.location or run_all:
        run_location_pipeline(config, target_name=args.location)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
