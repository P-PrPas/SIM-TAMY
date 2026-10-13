"""Load and pin a case: content/cases/<case_id>/{case,actions,rubric}.yaml."""

import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter, ValidationError

from app.domain.action import Action
from app.domain.case import Case
from app.domain.rubric import Rubric


@dataclass(frozen=True)
class Issue:
    file: str
    path: str  # dotted field path, "" for whole-file problems
    message: str

    def __str__(self) -> str:
        return f"{self.file}: {self.path or '-'}: {self.message}"


class ContentError(Exception):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("\n".join(map(str, issues)))
        self.issues = issues


@dataclass(frozen=True)
class LoadedCase:
    case: Case
    actions: list[Action]
    rubric: Rubric
    case_hash: str  # sha256 of the three files; pinned on the session (FR-CASE-05)


_FILES: dict[str, TypeAdapter[Any]] = {
    "case.yaml": TypeAdapter(Case),
    "actions.yaml": TypeAdapter(list[Action]),
    "rubric.yaml": TypeAdapter(Rubric),
}


def load_case(case_dir: Path) -> LoadedCase:
    issues: list[Issue] = []
    parsed: dict[str, Any] = {}
    digest = hashlib.sha256()
    for name, adapter in _FILES.items():
        path = case_dir / name
        if not path.is_file():
            issues.append(Issue(name, "", "file not found"))
            continue
        raw = path.read_bytes()
        digest.update(name.encode() + b"\0" + raw + b"\0")
        try:
            parsed[name] = adapter.validate_python(yaml.safe_load(raw))
        except yaml.YAMLError as exc:
            issues.append(Issue(name, "", f"invalid YAML: {exc}".replace("\n", " ")))
        except ValidationError as exc:
            issues += [Issue(name, ".".join(map(str, e["loc"])), e["msg"]) for e in exc.errors()]
    if not issues and parsed["case.yaml"].case_id != case_dir.name:
        issues.append(Issue("case.yaml", "case_id", f"must match folder name {case_dir.name!r}"))
    if issues:
        raise ContentError(issues)
    return LoadedCase(
        parsed["case.yaml"], parsed["actions.yaml"], parsed["rubric.yaml"], digest.hexdigest()
    )


class ContentStore:
    """Keeps every loaded version by hash, so a pinned session never sees a later edit."""

    def __init__(self, content_dir: Path) -> None:
        self.cases_dir = content_dir / "cases"
        self._by_hash: dict[tuple[str, str], LoadedCase] = {}

    def load(self, case_id: str) -> LoadedCase:
        loaded = load_case(self.cases_dir / case_id)
        self._by_hash[(case_id, loaded.case_hash)] = copy.deepcopy(loaded)
        return loaded

    def get(self, case_id: str, case_hash: str) -> LoadedCase | None:
        # ponytail: deepcopy per get (frozen models don't freeze inner lists); cheap at this size
        stored = self._by_hash.get((case_id, case_hash))
        return copy.deepcopy(stored) if stored else None
