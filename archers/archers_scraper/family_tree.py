from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import CharacterRecord


LOGGER = logging.getLogger(__name__)


def find_family_tree_file(root: Path) -> Path | None:
    for candidate in [
        root / "family_tree.json",
        root / "family_tree.mmd",
        root / "family_tree.gv",
        root / "family_tree.dot",
    ]:
        if candidate.exists():
            return candidate
    return None


def update_family_tree(path: Path, records: list[CharacterRecord], dry_run: bool) -> bool:
    if path.suffix != ".json":
        LOGGER.info("Family tree update skipped for unsupported format: %s", path.name)
        return False
    data = {
        "characters": [
            {
                "name": record.full_name,
                "parents": record.parents,
                "children": record.children,
                "partners": record.partners,
                "file": record.filename,
            }
            for record in sorted(records, key=lambda item: item.full_name.lower())
        ]
    }
    payload = json.dumps(data, indent=2) + "\n"
    if dry_run:
        LOGGER.info("Dry run: would update family tree %s", path)
        return True
    path.write_text(payload, encoding="utf-8")
    return True
