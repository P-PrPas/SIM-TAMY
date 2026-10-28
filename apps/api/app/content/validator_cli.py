"""`make validate-content [STRICT=1]`: exit 1 and print `file: field.path: message` on any error."""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from app.content.family import load_stories
from app.content.knowledge import load_knowledge
from app.content.loader import ContentError, load_case
from app.content.validate import check
from app.core.config import get_settings


def _check_knowledge(content_dir: Path) -> bool:
    """Validate sources, knowledge units, the release and learning paths; True when it failed."""
    if not (content_dir / "knowledge").is_dir():
        return False  # a content tree without the 2.0 knowledge base (e.g. a bare cases tree)
    try:
        kb = load_knowledge(content_dir)
    except ContentError as exc:
        for issue in exc.issues:
            print(issue, file=sys.stderr)
        return True
    print(
        f"OK knowledge {kb.release.id} ({len(kb.release.units)}/{len(kb.units)} units released, "
        f"{len(kb.sources)} sources, {len(kb.paths.stages)} stages)"
    )
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-content")
    parser.add_argument("--strict", action="store_true", help="require `source` on clinical items")
    args = parser.parse_args(argv)

    content_dir = get_settings().content_dir
    if not content_dir.is_dir():
        print(f"ERROR: CONTENT_DIR not found: {content_dir}", file=sys.stderr)
        return 1
    cases_dir = content_dir / "cases"
    dirs = sorted(p for p in cases_dir.iterdir() if p.is_dir()) if cases_dir.is_dir() else []
    if not dirs:
        print(f"no cases in {cases_dir}; nothing validated")
        return 0

    failed = _check_knowledge(content_dir)
    for d in dirs:
        try:
            loaded = load_case(d)
            issues = check(loaded, strict=args.strict)
        except ContentError as exc:
            issues = exc.issues
        for issue in issues:
            print(f"{d.name}/{issue}", file=sys.stderr)
        failed |= bool(issues)
        if not issues:
            print(f"OK {d.name} {loaded.case_hash[:12]}")
    try:
        for story in load_stories(content_dir):
            print(f"OK family/{story.id} {story.version} ({story.status})")
    except (ValidationError, ValueError) as exc:
        print(f"ERROR family stories: {exc}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
