from pathlib import Path
import unittest

from archers_scraper.config import ScraperConfig
from archers_scraper.merge import merge_character, merge_location
from archers_scraper.models import EntitySeed
from archers_scraper.sources.reference import WikipediaAdapter


FIXTURES = Path(__file__).parent / "fixtures"


class WikipediaParserTests(unittest.TestCase):
    def setUp(self) -> None:
        config = ScraperConfig(root=Path("/tmp"))
        self.adapter = WikipediaAdapter(config)

    def test_character_page_extracts_clean_fields(self) -> None:
        seed = EntitySeed(entity_type="character", full_name="Jill Archer", common_name="Jill")
        html = (FIXTURES / "wikipedia_jill_archer_page.html").read_text(encoding="utf-8")
        document = self.adapter._parse_page(seed, "https://en.wikipedia.org/wiki/Jill_Archer", html)
        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document.payload["actor_current"], "Patricia Greene")
        self.assertEqual(document.payload["partners"], ["Phil Archer (1957-2010)"])
        self.assertIn("fictional character from the BBC Radio 4 soap opera The Archers", document.payload["overview"])
        self.assertEqual(document.payload["first_introduced"], "1957")

    def test_character_page_rejects_wrong_target(self) -> None:
        seed = EntitySeed(entity_type="character", full_name="David Archer", common_name="David")
        html = (FIXTURES / "wikipedia_ruth_archer_page.html").read_text(encoding="utf-8")
        document = self.adapter._parse_page(seed, "https://en.wikipedia.org/wiki/Ruth_Archer", html)
        self.assertIsNone(document)

    def test_character_page_accepts_safe_first_name_variant(self) -> None:
        seed = EntitySeed(entity_type="character", full_name="Phil Archer", common_name="Phil")
        html = """
        <html><body>
          <h1 id="firstHeading">Philip Walter Archer</h1>
          <div class="mw-parser-output">
            <p>Philip Walter Archer is a fictional character from The Archers, played by Norman Painting. He made his first appearance on 29 May 1950, the show's pilot episode.</p>
          </div>
          <table class="infobox">
            <tr><th>Portrayed by</th><td>Norman Painting</td></tr>
          </table>
        </body></html>
        """
        document = self.adapter._parse_page(seed, "https://en.wikipedia.org/wiki/Phil_Archer", html)
        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual(document.payload["actor_current"], "Norman Painting")
        self.assertEqual(document.payload["first_introduced"], "29 May 1950")

    def test_location_page_extracts_summary_and_type(self) -> None:
        seed = EntitySeed(entity_type="location", full_name="Brookfield Farm", common_name="Brookfield Farm")
        html = (FIXTURES / "wikipedia_brookfield_farm_page.html").read_text(encoding="utf-8")
        document = self.adapter._parse_page(seed, "https://en.wikipedia.org/wiki/Brookfield_Farm", html)
        self.assertIsNotNone(document)
        assert document is not None
        record = merge_location(seed, [document])
        self.assertEqual(record.location_type, "Farm")
        self.assertIn("one of the main Archer family homes", record.overview)
        self.assertEqual(record.current_occupier_owner, ["David Archer", "Ruth Archer", "Pip Archer"])

    def test_character_merge_derives_children_role_and_home_from_overview(self) -> None:
        seed = EntitySeed(entity_type="character", full_name="Pat Archer", common_name="Pat")
        document = self.adapter.build_document(
            seed,
            "https://example.invalid/pat",
            {
                "overview": (
                    "Pat Archer is a fictional character from The Archers. "
                    "She is an organic farmer at Bridge Farm and lives at Bridge Farm with Tony Archer. "
                    "They have three children: John, Helen and Tom."
                ),
                "actor_current": "Patricia Gallimore",
                "first_introduced": "1974",
                "partners": ["Tony Archer (1974-present)"],
            },
            confidence=0.72,
        )
        record = merge_character(seed, [document])
        self.assertEqual(record.work_role, "Organic farmer at Bridge Farm")
        self.assertEqual(record.where_they_live_now, "Bridge Farm")
        self.assertEqual(record.children, ["John", "Helen", "Tom"])

    def test_character_merge_derives_role_from_named_occupation_phrase(self) -> None:
        seed = EntitySeed(entity_type="character", full_name="Usha Gupta", common_name="Usha")
        document = self.adapter.build_document(
            seed,
            "https://example.invalid/usha",
            {
                "overview": (
                    "Usha Gupta is a solicitor in Ambridge. "
                    "She lives in Ambridge and is a longstanding resident."
                ),
            },
            confidence=0.72,
        )
        record = merge_character(seed, [document])
        self.assertEqual(record.work_role, "Solicitor")
        self.assertEqual(record.where_they_live_now, "Ambridge")


if __name__ == "__main__":
    unittest.main()
