"""Export the three content YAML contracts as editor-ready JSON Schema (T-012)."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.domain.action import Action
from app.domain.case import Case
from app.domain.family import FamilyStory
from app.domain.rubric import Rubric

_DIALECT = "https://json-schema.org/draft/2020-12/schema"
_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "case.schema.json": TypeAdapter(Case),
    "actions.schema.json": TypeAdapter(list[Action]),
    "rubric.schema.json": TypeAdapter(Rubric),
    "family.schema.json": TypeAdapter(FamilyStory),
}


def default_schema_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "content" / "schemas"


def render_schemas() -> dict[str, str]:
    """Return stable UTF-8 JSON from the same Pydantic types used by the loader."""
    return {
        name: json.dumps(
            {"$schema": _DIALECT, **adapter.json_schema(mode="validation", by_alias=True)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
        for name, adapter in _ADAPTERS.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="export-content-schemas")
    parser.add_argument("--output-dir", type=Path, default=default_schema_dir())
    parser.add_argument(
        "--check", action="store_true", help="fail if exported files are missing or stale"
    )
    args = parser.parse_args(argv)
    rendered = render_schemas()

    if args.check:
        stale = [
            name
            for name, expected in rendered.items()
            if not (args.output_dir / name).is_file()
            or (args.output_dir / name).read_text(encoding="utf-8") != expected
        ]
        if stale:
            for name in stale:
                print(f"missing or stale schema: {args.output_dir / name}", file=sys.stderr)
            return 1
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in rendered.items():
        (args.output_dir / name).write_text(data, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
