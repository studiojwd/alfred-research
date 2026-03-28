import unittest

from archers_scraper.slugging import character_filename, ensure_unique_filename, location_filename, slugify


class SluggingTests(unittest.TestCase):
    def test_slugify_normalises_punctuation(self) -> None:
        self.assertEqual(slugify("Lower Loxley Hall"), "lower_loxley_hall")
        self.assertEqual(slugify("St Stephen's Church"), "st_stephen_s_church")

    def test_character_filename_uses_surname_first(self) -> None:
        self.assertEqual(character_filename("David Archer"), "archer_david.md")
        self.assertEqual(character_filename("Jack Archer", "1919"), "archer_jack_1919.md")

    def test_location_filename(self) -> None:
        self.assertEqual(location_filename("Brookfield Farm"), "brookfield_farm.md")

    def test_unique_filename_appends_counter(self) -> None:
        filename = ensure_unique_filename("archer_jack.md", {"archer_jack.md"}, None)
        self.assertEqual(filename, "archer_jack_2.md")


if __name__ == "__main__":
    unittest.main()
