"""Load the 2.0 knowledge base: source registry, knowledge units, release, learning paths.

Files: `content/knowledge/sources.yaml`, `content/knowledge/units/<id>.yaml`,
`content/curriculum/paths.yaml`. Every problem is reported as `file: field.path: message` (like
the case loader) and fails `make validate-content`.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter, ValidationError

from app.content.family import load_stories
from app.content.loader import ContentError, Issue
from app.domain.curriculum import LearningPaths
from app.domain.knowledge import KnowledgeRelease, KnowledgeUnit, SourceRecord

_SOURCES = TypeAdapter(list[SourceRecord])


@dataclass(frozen=True)
class KnowledgeBase:
    sources: tuple[SourceRecord, ...]
    units: tuple[KnowledgeUnit, ...]  # every unit on disk, including draft and retired
    release: KnowledgeRelease  # only published units with a usable rights status
    paths: LearningPaths

    def source(self, source_id: str) -> SourceRecord | None:
        return next((s for s in self.sources if s.id == source_id), None)


def _read(path: Path, rel: str, issues: list[Issue]) -> Any:
    try:
        return yaml.safe_load(path.read_text("utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        issues.append(Issue(rel, "", f"cannot read: {exc}"))
        return None


def _validation_issues(rel: str, exc: ValidationError) -> list[Issue]:
    return [Issue(rel, ".".join(map(str, e["loc"])), e["msg"]) for e in exc.errors()]


def _load_sources(content_dir: Path, issues: list[Issue]) -> list[SourceRecord]:
    rel = "knowledge/sources.yaml"
    raw = _read(content_dir / "knowledge" / "sources.yaml", rel, issues)
    if raw is None:
        return []
    try:
        sources = _SOURCES.validate_python(raw)
    except ValidationError as exc:
        issues += _validation_issues(rel, exc)
        return []
    seen: set[str] = set()
    for s in sources:
        if s.id in seen:
            issues.append(Issue(rel, s.id, "duplicate source ID"))
        seen.add(s.id)
    return sources


def _load_units(
    content_dir: Path, sources: list[SourceRecord], issues: list[Issue]
) -> list[KnowledgeUnit]:
    known = {s.id for s in sources}
    units: list[KnowledgeUnit] = []
    for path in sorted((content_dir / "knowledge" / "units").glob("*.yaml")):
        rel = f"knowledge/units/{path.name}"
        raw = _read(path, rel, issues)
        if raw is None:
            continue
        try:
            unit = KnowledgeUnit.model_validate(raw)
        except ValidationError as exc:
            issues += _validation_issues(rel, exc)
            continue
        if path.stem != unit.id:
            issues.append(Issue(rel, "id", f"file name must be {unit.id}.yaml"))
        if any(u.id == unit.id for u in units):
            issues.append(Issue(rel, "id", "duplicate unit ID"))
        for claim in unit.claims:
            for loc in claim.locators:
                if loc.source_id not in known:
                    msg = f"unknown source_id {loc.source_id}"
                    issues.append(Issue(rel, f"claims.{claim.id}.locators", msg))
        units.append(unit)
    return units


def _playable_ids(content_dir: Path) -> set[str]:
    cases_dir = content_dir / "cases"
    cases = (
        {p.name for p in cases_dir.iterdir() if (p / "case.yaml").is_file()}
        if cases_dir.is_dir()
        else set()
    )
    return {s.id for s in load_stories(content_dir)} | cases


def _check_references(
    content_dir: Path, paths: LearningPaths, release: KnowledgeRelease, issues: list[Issue]
) -> None:
    rel = "curriculum/paths.yaml"
    playable = _playable_ids(content_dir)
    for stage in paths.stages:
        for obj in stage.objectives:
            for uid in obj.unit_ids:
                if release.unit(uid) is None:
                    issues.append(Issue(rel, obj.id, f"unit {uid} is not in the release"))
            for sid in obj.story_ids:
                if sid not in playable:
                    issues.append(Issue(rel, obj.id, f"story or case {sid} does not exist"))
    objectives = paths.objective_ids()
    for story in load_stories(content_dir):
        # Stream B adds these optional fields to FamilyStory; read them defensively.
        file = f"family/{story.id}.yaml"
        for uid in getattr(story, "knowledge_unit_ids", []):
            if release.unit(uid) is None:
                issues.append(
                    Issue(file, "knowledge_unit_ids", f"unit {uid} is not in the release")
                )
        for oid in getattr(story, "objective_ids", []):
            if oid not in objectives:
                issues.append(Issue(file, "objective_ids", f"unknown objective {oid}"))


def load_knowledge(content_dir: Path) -> KnowledgeBase:
    """Raise ContentError listing every problem found; otherwise return the checked base."""
    issues: list[Issue] = []
    sources = _load_sources(content_dir, issues)
    units = _load_units(content_dir, sources, issues)
    release = KnowledgeRelease.build(units)

    rel = "curriculum/paths.yaml"
    raw = _read(content_dir / "curriculum" / "paths.yaml", rel, issues)
    paths: LearningPaths | None = None
    if raw is not None:
        try:
            paths = LearningPaths.model_validate(raw)
        except ValidationError as exc:
            issues += _validation_issues(rel, exc)
    if paths is not None:
        _check_references(content_dir, paths, release, issues)
    if issues or paths is None:
        raise ContentError(issues)
    return KnowledgeBase(tuple(sources), tuple(units), release, paths)


@lru_cache
def cached_knowledge(content_dir: Path) -> KnowledgeBase:
    """Per-process cache; tests that change content call `cached_knowledge.cache_clear()`."""
    return load_knowledge(content_dir)
