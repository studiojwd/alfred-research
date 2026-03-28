from __future__ import annotations

import re
from urllib.parse import urljoin

from .base import BaseSourceAdapter
from ..models import EntitySeed, SourceDocument


FIRST_NAME_VARIANTS = {
    "phil": {"phil", "philip"},
    "pat": {"pat", "patricia"},
    "kate": {"kate", "katherine", "catherine"},
    "jack": {"jack", "john"},
    "will": {"will", "william"},
}


class WikipediaAdapter(BaseSourceAdapter):
    source_name = "en.wikipedia.org"
    priority = 3
    search_path_template = "https://en.wikipedia.org/w/index.php?search={query}%20the%20archers"

    def parse_search(self, seed: EntitySeed, search_url: str, html: str) -> list[SourceDocument]:
        soup = self.soup(html)
        documents: list[SourceDocument] = []
        candidate_links = soup.select(".mw-search-results a")
        if not candidate_links:
            canonical = soup.select_one("link[rel='canonical']")
            if canonical and canonical.get("href") and "/wiki/" in canonical.get("href", ""):
                page_url = canonical["href"]
                document = self._parse_page(seed, page_url, html)
                return [document] if document else []
        ranked_links = sorted(
            candidate_links[:10],
            key=lambda link: self._title_match_score(seed, (link.get("title") or " ".join(link.stripped_strings)).strip()),
            reverse=True,
        )
        for link in ranked_links:
            title = (link.get("title") or " ".join(link.stripped_strings)).strip()
            if not title or self._title_match_score(seed, title) <= 0:
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
        page_title = ""
        heading = soup.select_one("#firstHeading")
        if heading:
            page_title = self._clean_text(heading.get_text(" ", strip=True))
            if not self._page_matches_target(seed, page_title):
                return None
        overview = ""
        paragraph_texts: list[str] = []
        for paragraph in soup.select(".mw-parser-output > p"):
            text = self._clean_text(" ".join(paragraph.stripped_strings))
            if text:
                paragraph_texts.append(text)
            if self._is_meaningful_paragraph(seed, text):
                overview = text
                break
        if overview and not self._overview_matches_target(seed, overview):
            return None
        actor_names: list[str] = []
        first_introduced = ""
        born = ""
        spouses: list[str] = []
        children: list[str] = []
        location_type = ""
        current_people: list[str] = []
        for row in soup.select("table.infobox tr"):
            header = row.find("th")
            value_cell = row.find("td")
            if not header or not value_cell:
                continue
            key = header.get_text(" ", strip=True).casefold()
            value = self._clean_text(value_cell.get_text(" ", strip=True))
            if "portray" in key or "played by" in key or "actor" in key:
                actor_names.extend(self._split_names(value))
            if "first appearance" in key and not first_introduced:
                first_introduced = value
            if "born" in key and not born:
                born = value
            if "spouse" in key or "husband" in key or "wife" in key:
                spouses.extend(self._split_names(value))
            if "children" in key:
                children.extend(self._split_names(value))
            if seed.entity_type == "location":
                if key in {"type", "location type"} and not location_type:
                    location_type = value
                if any(term in key for term in {"owned by", "owner", "resident", "residents", "occupants", "occupied by"}):
                    current_people.extend(self._split_names(value))
        payload: dict[str, str | list[str]] = {}
        if overview:
            if seed.entity_type == "location":
                payload["location_overview"] = overview
            else:
                payload["overview"] = overview
        if seed.entity_type == "location":
            if location_type:
                payload["location_type"] = location_type
            if current_people:
                payload["current_occupier_owner"] = list(dict.fromkeys(current_people))
        else:
            if actor_names:
                payload["actor_current"] = actor_names[0]
                if len(actor_names) > 1:
                    payload["actor_past"] = actor_names[1:]
            if first_introduced:
                payload["first_introduced"] = first_introduced
            elif paragraph_texts:
                inferred = self._infer_first_introduced(paragraph_texts)
                if inferred:
                    payload["first_introduced"] = inferred
            if born:
                payload["born"] = born
            if spouses:
                payload["partners"] = spouses
            if children:
                payload["children"] = children
        if not payload:
            return None
        return self.build_document(
            seed,
            page_url,
            payload,
            confidence=0.72,
            notes=["Extracted from a Wikipedia article page rather than a search result page."],
        )

    def _is_candidate_title(self, seed: EntitySeed, title: str) -> bool:
        return self._title_match_score(seed, title) > 0

    def _title_match_score(self, seed: EntitySeed, title: str) -> int:
        lowered = title.casefold()
        target = seed.full_name.casefold()
        first = target.split()[0]
        surname = target.split()[-1]
        score = 0
        if target == lowered:
            score += 5
        if target in lowered:
            score += 4
        if first in lowered:
            score += 2
        if surname in lowered:
            score += 2
        if "archers" in lowered:
            score += 1
        if "disambiguation" in lowered:
            score -= 5
        return score

    def _page_matches_target(self, seed: EntitySeed, title: str) -> bool:
        return self._name_matches_target(seed, title)

    def _is_meaningful_paragraph(self, seed: EntitySeed, text: str) -> bool:
        lowered = text.casefold()
        if len(text) < 80:
            return False
        if seed.entity_type == "location":
            if seed.full_name.casefold().split()[0] not in lowered and seed.full_name.casefold() not in lowered:
                return False
            return "the archers" in lowered or "ambridge" in lowered
        if seed.full_name.casefold().split()[0] not in lowered:
            return False
        return "the archers" in lowered or "bbc radio" in lowered or "ambridge" in lowered

    def _overview_matches_target(self, seed: EntitySeed, text: str) -> bool:
        if seed.entity_type == "location":
            lowered = text.casefold()
            target = seed.full_name.casefold()
            return target in lowered or target.split()[0] in lowered
        return self._name_matches_target(seed, text)

    def _name_matches_target(self, seed: EntitySeed, text: str) -> bool:
        lowered = text.casefold()
        target_parts = seed.full_name.casefold().split()
        if len(target_parts) < 2:
            return seed.full_name.casefold() in lowered
        first_name = target_parts[0]
        surname = target_parts[-1]
        if surname not in lowered:
            return False
        variants = FIRST_NAME_VARIANTS.get(first_name, {first_name})
        return any(re.search(rf"\b{re.escape(variant)}\b", lowered) for variant in variants)

    def _split_names(self, value: str) -> list[str]:
        cleaned = self._clean_text(value)
        cleaned = re.sub(r"\)\s+(?=[A-Z])", "); ", cleaned)
        parts = re.split(r";|/|\band\b", cleaned)
        return [part.strip(" ,") for part in parts if part.strip(" ,")]

    def _clean_text(self, text: str) -> str:
        cleaned = re.sub(r"\[\s*\d+\s*\]", "", text)
        cleaned = re.sub(r"\s+\)", ")", cleaned)
        cleaned = re.sub(r"\(\s+", "(", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
        cleaned = re.sub(r"'\s+([^']+?)\s+'", r"'\1'", cleaned)
        cleaned = re.sub(r"\(\s*nee\s+([^)]+)\)", r"(née \1)", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _infer_first_introduced(self, paragraphs: list[str]) -> str:
        for text in paragraphs[:4]:
            match = re.search(
                r"\bfirst appearance on\s+(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})\b",
                text,
                re.IGNORECASE,
            )
            if match:
                return match.group(1)
            match = re.search(r"\b(?:since|from)\s+(19\d{2}|20\d{2})\b", text, re.IGNORECASE)
            if match:
                return match.group(1)
            match = re.search(r"\bintroduced\b.*?\b(19\d{2}|20\d{2})\b", text, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""


class ReferenceWikiAdapter(BaseSourceAdapter):
    source_name = "thearchers.wiki"
    priority = 4
    search_path_template = "https://thearchers.wiki/index.php?search={query}"

    def parse_search(self, seed: EntitySeed, search_url: str, html: str) -> list[SourceDocument]:
        soup = self.soup(html)
        page_heading = soup.select_one("#firstHeading")
        overview = ""
        for paragraph in soup.select(".mw-parser-output > p"):
            text = " ".join(paragraph.stripped_strings)
            if len(text) >= 80:
                overview = text
                break
        payload: dict[str, str] = {}
        if overview:
            payload["overview"] = overview
        elif page_heading:
            payload["overview"] = page_heading.get_text(strip=True)
        if not payload:
            return []
        return [
            self.build_document(
                seed,
                search_url,
                payload,
                confidence=0.45,
                notes=["Continuity-only source; suitable for filling gaps and flagging uncertainty."],
            )
        ]
