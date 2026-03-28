from __future__ import annotations

import re
from urllib.parse import urljoin

from .base import BaseSourceAdapter
from ..models import EntitySeed, SourceDocument


class RadioTimesAdapter(BaseSourceAdapter):
    source_name = "radiotimes.com"
    priority = 2
    search_path_template = "https://www.radiotimes.com/search/?q={query}%20the%20archers"

    def parse_search(self, seed: EntitySeed, search_url: str, html: str) -> list[SourceDocument]:
        soup = self.soup(html)
        documents: list[SourceDocument] = []
        for link in soup.select("a[href*='/audio/'], a[href*='/tv/'], a[href*='/radio/']")[:8]:
            title = " ".join(link.stripped_strings).strip()
            if not title or not self._is_candidate_title(seed, title):
                continue
            page_url = urljoin(search_url, link.get("href", ""))
            page_html = self.fetch_page(page_url)
            if not page_html:
                continue
            document = self._parse_page(seed, page_url, page_html)
            if document:
                documents.append(document)
                break
        return documents

    def _parse_page(self, seed: EntitySeed, page_url: str, html: str) -> SourceDocument | None:
        soup = self.soup(html)
        description = ""
        meta_description = soup.select_one("meta[name='description'], meta[property='og:description']")
        if meta_description and meta_description.get("content"):
            description = meta_description["content"].strip()
        paragraphs = []
        for selector in ["article p", "[data-testid='article-body'] p", "main p"]:
            for paragraph in soup.select(selector):
                text = " ".join(paragraph.stripped_strings)
                if self._is_meaningful_paragraph(seed, text):
                    paragraphs.append(text)
            if paragraphs:
                break
        overview = paragraphs[0] if paragraphs else ""
        actor_mentions = []
        scan_text = " ".join(paragraphs[:3]) or description
        for match in re.finditer(r"(played by|portrayed by)\s+([A-Z][A-Za-z' -]+)", scan_text):
            actor_mentions.append(match.group(2).strip())
        payload: dict[str, str | list[str]] = {}
        if description and self._is_meaningful_paragraph(seed, description):
            if seed.entity_type == "location":
                payload["location_overview"] = description
            else:
                payload["overview"] = description
        elif overview:
            if seed.entity_type == "location":
                payload["location_overview"] = overview
            else:
                payload["overview"] = overview
        if actor_mentions and seed.entity_type == "character":
            payload["actor_current"] = actor_mentions[0]
        if not payload:
            return None
        return self.build_document(
            seed,
            page_url,
            payload,
            confidence=0.66,
            notes=["Extracted from a Radio Times article page rather than a search result tile."],
        )

    def _is_candidate_title(self, seed: EntitySeed, title: str) -> bool:
        lowered = title.casefold()
        target = seed.full_name.casefold()
        first = target.split()[0]
        return first in lowered or target in lowered

    def _is_meaningful_paragraph(self, seed: EntitySeed, text: str) -> bool:
        lowered = text.casefold()
        if len(text) < 80:
            return False
        if seed.full_name.split()[0].casefold() not in lowered and seed.full_name.casefold() not in lowered:
            return False
        if lowered in {"on tv now", "the archers"}:
            return False
        return True


class UmraAdapter(BaseSourceAdapter):
    source_name = "umra.fandom.com"
    priority = 5
    search_path_template = "https://umra.fandom.com/wiki/Special:Search?query={query}"

    def parse_search(self, seed: EntitySeed, search_url: str, html: str) -> list[SourceDocument]:
        soup = self.soup(html)
        title = soup.title.string.strip() if soup.title and soup.title.string else seed.full_name
        return [
            self.build_document(
                seed,
                search_url,
                {"overview": title},
                confidence=0.35,
                notes=["Legacy continuity source; verify against stronger sources before trusting specific facts."],
            )
        ]
