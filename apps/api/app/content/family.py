"""Load and validate family stories without exposing them through a static web bundle."""

from pathlib import Path

import yaml

from app.domain.family import FamilyStory


def load_stories(content_dir: Path) -> list[FamilyStory]:
    return [
        FamilyStory.model_validate(yaml.safe_load(path.read_text("utf-8")))
        for path in sorted((content_dir / "family").glob("*.yaml"))
    ]
