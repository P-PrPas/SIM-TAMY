"""Loader file errors, version pinning (FR-CASE-05), frozen models, and the CLI exit codes."""

from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.loader import ContentError, ContentStore, load_case
from app.content.validator_cli import main
from app.core.config import get_settings


def test_missing_and_malformed_files_are_reported_per_file(
    build: Callable[..., Path],
) -> None:
    case_dir = build()
    (case_dir / "rubric.yaml").unlink()
    (case_dir / "actions.yaml").write_text("- id: [unclosed", encoding="utf-8")

    with pytest.raises(ContentError) as info:
        load_case(case_dir)

    found = {(i.file, i.message.split(":")[0]) for i in info.value.issues}
    assert ("rubric.yaml", "file not found") in found and ("actions.yaml", "invalid YAML") in found


def test_pinned_version_survives_a_later_edit(build: Callable[..., Path]) -> None:
    case_dir = build()
    store = ContentStore(case_dir.parents[1])
    old = store.load("TEST-001")

    path = case_dir / "case.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("title_th: t", "title_th: edited"))
    new = store.load("TEST-001")

    assert new.case_hash != old.case_hash and new.case.title_th == "edited"
    pinned = store.get("TEST-001", old.case_hash)
    assert pinned is not None and pinned.case.title_th == "t"


def test_resolve_finds_a_pinned_version_even_after_a_restart(build: Callable[..., Path]) -> None:
    case_dir = build()
    pinned = ContentStore(case_dir.parents[1]).load("TEST-001")

    restarted = ContentStore(case_dir.parents[1])  # empty memory, same files
    again = restarted.resolve("TEST-001", pinned.case_hash)
    assert again is not None and again.case_hash == pinned.case_hash

    path = case_dir / "case.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("title_th: t", "title_th: edited"))
    assert ContentStore(case_dir.parents[1]).resolve("TEST-001", pinned.case_hash) is None
    assert restarted.resolve("TEST-001", pinned.case_hash) is not None  # still held in memory
    assert restarted.resolve("MISSING", "0" * 64) is None


def test_same_files_give_same_hash(build: Callable[..., Path]) -> None:
    case_dir = build()
    assert load_case(case_dir).case_hash == load_case(case_dir).case_hash


def test_loaded_case_is_immutable(build: Callable[..., Path]) -> None:
    case = load_case(build()).case
    with pytest.raises(ValidationError):
        case.title_th = "changed"  # type: ignore[misc]


@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch) -> Callable[[Path, list[str]], int]:
    def _run(content_dir: Path, args: list[str]) -> int:
        monkeypatch.setenv("CONTENT_DIR", str(content_dir))
        get_settings.cache_clear()
        try:
            return main(args)
        finally:
            get_settings.cache_clear()

    return _run


def test_cli_ok_on_valid_case(
    build: Callable[..., Path], cli: Callable[..., int], capsys: pytest.CaptureFixture[str]
) -> None:
    case_dir = build()
    assert cli(case_dir.parents[1], ["--strict"]) == 0
    assert "OK TEST-001" in capsys.readouterr().out


def test_cli_fails_with_file_and_field_path(
    build: Callable[..., Path], cli: Callable[..., int], capsys: pytest.CaptureFixture[str]
) -> None:
    case_dir = build(lambda d: d["case.yaml"]["facts"][1].pop("leak_terms_th"))
    assert cli(case_dir.parents[1], []) == 1
    assert "TEST-001/case.yaml: facts.1.hidden.leak_terms_th" in capsys.readouterr().err


def test_cli_strict_flag_changes_the_result(
    build: Callable[..., Path], cli: Callable[..., int]
) -> None:
    case_dir = build(lambda d: d["rubric.yaml"]["items"][0].pop("source"))
    assert cli(case_dir.parents[1], []) == 0
    assert cli(case_dir.parents[1], ["--strict"]) == 1


def test_cli_with_no_cases_says_nothing_was_validated(
    tmp_path: Path, cli: Callable[..., int], capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "cases").mkdir()
    assert cli(tmp_path, []) == 0
    assert "nothing validated" in capsys.readouterr().out


def test_cli_missing_content_dir_is_an_error(tmp_path: Path, cli: Callable[..., int]) -> None:
    assert cli(tmp_path / "nope", []) == 1


def test_mutating_a_returned_case_does_not_change_the_pinned_one(
    build: Callable[..., Path],
) -> None:
    store = ContentStore(build().parents[1])
    first = store.load("TEST-001")
    first.actions.clear()
    first.case.facts.clear()  # frozen=True does not stop this; the store must

    again = store.get("TEST-001", first.case_hash)
    assert again is not None and again.actions and again.case.facts
    again.actions.clear()
    refetched = store.get("TEST-001", first.case_hash)
    assert refetched is not None and refetched.actions
