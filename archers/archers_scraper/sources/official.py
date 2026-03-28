from __future__ import annotations

from urllib.parse import urljoin

from .base import BaseSourceAdapter
from ..models import EntitySeed, SourceDocument


class OfficialArchersAdapter(BaseSourceAdapter):
    source_name = "thearchers.co.uk"
    priority = 1
    search_path_template = "https://www.thearchers.co.uk/search/?q={query}"

    def parse_search(self, seed: EntitySeed, search_url: str, html: str) -> list[SourceDocument]:
        soup = self.soup(html)
        documents: list[SourceDocument] = []
        for link in soup.select("a[href*='/characters/'], a[href*='/episodes/'], a[href*='/news/']")[:3]:
            href = link.get("href")
            if not href:
                continue
            title = " ".join(link.stripped_strings) or seed.full_name
            payload = {
                "overview": title,
                "work_role": title if seed.entity_type == "character" else "",
                "location_overview": title if seed.entity_type == "location" else "",
            }
            documents.append(
                self.build_document(
                    seed,
                    urljoin(search_url, href),
                    payload,
                    confidence=0.9,
                    notes=["Search result title captured from official site; deeper page parsing can refine this."],
                )
            )
        return documents
