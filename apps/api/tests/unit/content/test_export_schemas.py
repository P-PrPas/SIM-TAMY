"""T-012: generated authoring schemas stay aligned with the Pydantic contract."""

import json
from pathlib import Path

from app.content.export_schemas import default_schema_dir, main, render_schemas


def test_export_has_the_three_loader_documents_and_validation_dialect() -> None:
    rendered = render_schemas()

    assert set(rendered) == {"case.schema.json", "actions.schema.json", "rubric.schema.json"}
    assert all(text.endswith("\n") for text in rendered.values())
    assert all(
        json.loads(text)["$schema"].endswith("/draft/2020-12/schema") for text in rendered.values()
    )

    case = json.loads(rendered["case.schema.json"])
    actions = json.loads(rendered["actions.schema.json"])
    rubric = json.loads(rendered["rubric.schema.json"])
    assert {"case_id", "status", "facts", "branch_rules"} <= set(case["required"])
    assert case["properties"]["status"]["enum"] == ["Draft", "In Review", "Approved"]
    assert "from" in case["$defs"]["BranchRule"]["properties"]
    assert "from_" not in case["$defs"]["BranchRule"]["properties"]
    assert actions["type"] == "array" and actions["items"]
    assert {"competencies", "items"} <= set(rubric["required"])


def test_export_check_detects_missing_or_stale_files_without_writing(tmp_path: Path) -> None:
    output_dir = tmp_path / "schemas"
    args = ["--output-dir", str(output_dir)]

    assert main([*args, "--check"]) == 1
    assert not output_dir.exists()
    assert main(args) == 0
    assert main([*args, "--check"]) == 0

    stale = output_dir / "case.schema.json"
    stale.write_text("{}\n", encoding="utf-8")
    assert main([*args, "--check"]) == 1
    assert stale.read_text(encoding="utf-8") == "{}\n"
    assert main(args) == 0
    assert main([*args, "--check"]) == 0


def test_committed_schemas_match_pydantic_models() -> None:
    assert default_schema_dir().is_dir()
    assert main(["--check"]) == 0
