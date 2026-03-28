from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class SourceConfig:
    name: str
    base_url: str
    priority: int
    enabled: bool = True


@dataclass(slots=True)
class ScraperConfig:
    root: Path
    user_agent: str = "archers-encyclopedia-bot/0.1 (+https://example.invalid)"
    timeout_seconds: int = 10
    retries: int = 2
    retry_backoff_seconds: float = 1.5
    rate_limit_seconds: float = 1.0
    max_source_failures: int = 3
    use_llm: bool = False
    llm_model: str = "gpt-4o-mini"
    research_mode: bool = False
    update_existing: bool = False
    create_missing_only: bool = False
    dry_run: bool = False
    source_priority: list[SourceConfig] = field(default_factory=list)

    @property
    def characters_dir(self) -> Path:
        return self.root / "characters"

    @property
    def locations_dir(self) -> Path:
        return self.root / "locations"

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def character_index_path(self) -> Path:
        return self.characters_dir / "the_archers_characters.md"

    @property
    def location_index_path(self) -> Path:
        return self.locations_dir / "the_archers_locations.md"

    @property
    def character_template_path(self) -> Path:
        return self.templates_dir / "character_template.md"

    @property
    def location_template_path(self) -> Path:
        return self.templates_dir / "location_template.md"

    @property
    def research_log_path(self) -> Path:
        return self.logs_dir / "research_notes.md"


def default_source_priority() -> list[SourceConfig]:
    return [
        SourceConfig("official", "https://www.thearchers.co.uk", 1),
        SourceConfig("radiotimes", "https://www.radiotimes.com", 2),
        SourceConfig("wikipedia", "https://en.wikipedia.org", 3),
        SourceConfig("thearcherswiki", "https://thearchers.wiki", 4),
        SourceConfig("umra", "https://umra.fandom.com", 5),
    ]
