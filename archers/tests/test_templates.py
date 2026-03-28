import unittest

from archers_scraper.models import CharacterRecord, LocationRecord
from archers_scraper.templates import render_character_markdown, render_location_markdown


CHARACTER_TEMPLATE = """# Full Name

## Character Overview
Write a detailed but readable summary of who the character is, why they matter, and how they fit into the wider world of Ambridge.

## DOB
- **Verified DOB:** 

## First Introduced
- **Verified first appearance date or year:** 

## Where They Live Now
State the current home if verified.
If not clearly verified, state the best supported current situation and explain any uncertainty in **Uncertain Details**.

## Parents
- 
- 

## Siblings
- 
- 

## Partners / Spouses / Exes
- **Name** — brief relationship note
- **Name** — brief relationship note

## Children
- 
- 

## Work / Role
Describe occupation, business role, farm role, church role, social role, or other importance in Ambridge.

## Relationship Summary
Write a connected summary of the character’s most important romantic, family, friendship, feud, and social relationships.

## Key Storylines / Timeline

### Early life
-

### Major adult storylines
-

### Recent position
-

## Fun Facts
Only include facts that can be reasonably supported.

- 
- 
- 

## Actor

### Current actor
- **Name** — years

### Past actors
- **Name** — years
- **Name** — years

## Uncertain Details
List anything not fully verified.

- 
- 
- 

## File Notes
- **Last updated:** 
- **Confidence level:** 
- **Related files:** 
"""

LOCATION_TEMPLATE = """# Location Name

## Location Type
Farm, house, pub, estate, business, hall, church, hotel, shop, village feature, or other.

## Location Overview
Write a detailed overview of what the location is, why it matters, and how it fits into the world of *The Archers*.

## Who Currently Lives Here / Owns It
- 
- 

If not applicable, write: Not applicable.

## Who Lived Here / Owned It In The Past
- **Name** — relationship to location
- **Name** — dates or era if known

## Key Storylines That Happened Here

### Early notable events
-

### Major storylines
-

### Recent significance
-

## Related Characters
- 
- 

## Uncertain Details
List anything not fully verified.

- 
- 
- 

## File Notes
- **Last updated:** 
- **Confidence level:** 
- **Related files:** 
"""


class TemplateRenderTests(unittest.TestCase):
    def test_render_character_markdown(self) -> None:
        record = CharacterRecord(
            full_name="David Archer",
            overview="David Archer is a long-running Brookfield farmer.",
            parents=["Phil Archer", "Jill Archer"],
            siblings=["Shula Hebden Lloyd", "Kenton Archer"],
            partners=["Ruth Archer — wife"],
            children=["Pip Archer", "Josh Archer", "Ben Archer"],
            work_role="Farmer at Brookfield Farm.",
            relationship_summary="Closely tied to the Archer family and Brookfield.",
            timeline_early_life=["Raised at Brookfield."],
            timeline_major_storylines=["Took on the running of Brookfield."],
            timeline_recent_position=["Still central to Brookfield life."],
            fun_facts=["Often associated with Brookfield."],
            actor_current="Timothy Bentinck — current era",
            actor_past=["Unknown"],
            uncertain_details=["Exact birth date still needs verifying."],
            related_files=["brookfield_farm.md"],
        )
        rendered = render_character_markdown(CHARACTER_TEMPLATE, record, "Medium")
        self.assertIn("# David Archer", rendered)
        self.assertIn("## Parents\n- Phil Archer\n- Jill Archer", rendered)
        self.assertIn("## Work / Role\nFarmer at Brookfield Farm.", rendered)
        self.assertIn("Confidence level:** Medium", rendered)

    def test_render_location_markdown(self) -> None:
        record = LocationRecord(
            full_name="Brookfield Farm",
            location_type="Farm",
            overview="Brookfield Farm is one of the main Archer family farms.",
            current_occupier_owner=["David Archer", "Ruth Archer"],
            past_occupier_owner=["Phil Archer — former farmer"],
            storylines_early=["Established as a key Archer setting."],
            storylines_major=["Used for major family farming storylines."],
            storylines_recent=["Still active in current storylines."],
            related_characters=["David Archer", "Ruth Archer"],
            uncertain_details=["Ownership details may need tighter sourcing."],
            related_files=["archer_david.md"],
        )
        rendered = render_location_markdown(LOCATION_TEMPLATE, record, "High")
        self.assertIn("# Brookfield Farm", rendered)
        self.assertIn("## Location Type\nFarm", rendered)
        self.assertIn("## Related Characters\n- David Archer\n- Ruth Archer", rendered)
        self.assertIn("Confidence level:** High", rendered)


if __name__ == "__main__":
    unittest.main()
