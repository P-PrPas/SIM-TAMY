"""Measure offline regression suites; publish counts, never hard-coded pass rates."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "apps/api"
SUITES = {
    "phrasing": ["ai/test_lexical.py", "ai/test_action_devset.py"],
    "reliability": ["engine/test_rescore_determinism.py", "engine/test_properties.py"],
    "safety": ["engine/test_scoring_gate.py", "engine/test_decision.py"],
    "consistency": ["ai/test_generator_validator.py", "ai/test_course_personas.py"],
}


def counts(path: Path, returncode: int) -> dict[str, int]:
    result = dict(passed=0, failed=0, errors=0, skipped=0)
    if path.exists():
        for case in ET.parse(path).iter("testcase"):
            key = next(
                (tag for tag in ("failure", "error", "skipped") if case.find(tag) is not None), None
            )
            result[
                {"failure": "failed", "error": "errors", "skipped": "skipped", None: "passed"}[key]
            ] += 1
    if returncode not in (0, 1) or not sum(result.values()):
        result["errors"] += 1
    if returncode == 1 and not (result["failed"] or result["errors"]):
        result["errors"] += 1
    return result


def fingerprint() -> str:
    digest = hashlib.sha256()
    paths = [
        path
        for directory in (
            "app/engine",
            "app/ai",
            "app/domain",
            "tests/unit/engine",
            "tests/unit/ai",
        )
        for path in (API / directory).rglob("*.py")
    ]
    paths += list((API / "app/ai/prompts").glob("*"))
    paths += list((ROOT / "content/cases").rglob("*.yaml"))
    paths += [API / "app/services/patient_voice.py"]
    for path in sorted(set(paths)):
        if path.is_file():
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "apps/web/public/validation-results.json"
    )
    args = parser.parse_args()
    scratch = API / ".tmp"
    scratch.mkdir(exist_ok=True)
    groups = []
    with tempfile.TemporaryDirectory(prefix="validation-", dir=scratch) as folder:
        for name, files in SUITES.items():
            xml = Path(folder) / f"{name}.xml"
            command = [
                sys.executable,
                "-m",
                "pytest",
                *[f"tests/unit/{file}" for file in files],
                "-q",
                f"--junitxml={xml}",
                f"--basetemp={folder}/{name}",
            ]
            run = subprocess.run(command, cwd=API, capture_output=True, timeout=180)
            group = {"id": name, **counts(xml, run.returncode)}
            groups.append(group)
            print(name, group)
    data = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "scope": "offline-unit",
        "fingerprint": fingerprint(),
        "groups": groups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(data, separators=(",", ":")) + "\n").encode())
    return int(any(group["failed"] or group["errors"] or group["skipped"] for group in groups))


if __name__ == "__main__":
    sys.exit(main())
