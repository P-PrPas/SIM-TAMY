"""docs/openapi.yaml is the contract (API_DESIGN 13); FastAPI's spec may not drift from it.

Incremental by design: only what the backend implements is compared, so this tightens itself as
endpoints land (T-040+). It checks paths, methods, operationIds, and for every schema name present
in both: property names, types/enums, and that anything the spec requires is required in code.
"""

from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate

from app.main import app

SPEC: dict[str, Any] = yaml.safe_load(
    (Path(__file__).resolve().parents[4] / "docs" / "openapi.yaml").read_text(encoding="utf-8")
)
METHODS = {"get", "post", "put", "patch", "delete"}


def drift(generated: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for path, item in generated["paths"].items():
        if path not in spec["paths"]:
            problems.append(f"path {path} is not in the spec")
            continue
        for method in METHODS & set(item):
            op = spec["paths"][path].get(method)
            if op is None:
                problems.append(f"{method.upper()} {path} is not in the spec")
            elif item[method].get("operationId") != op.get("operationId"):
                problems.append(f"{method.upper()} {path}: operationId differs from the spec")

    spec_schemas = spec["components"]["schemas"]
    for name, schema in generated.get("components", {}).get("schemas", {}).items():
        if name not in spec_schemas:
            continue  # FastAPI helper schemas (HTTPValidationError, ...)
        want = spec_schemas[name]
        props, want_props = schema.get("properties", {}), want.get("properties", {})
        if set(props) != set(want_props):
            problems.append(f"{name}: properties {sorted(props)} != spec {sorted(want_props)}")
        if not set(want.get("required", [])) <= set(schema.get("required", [])):
            problems.append(f"{name}: a field the spec requires is optional in code")
        for field in set(props) & set(want_props):
            for key in ("type", "enum"):
                if props[field].get(key) != want_props[field].get(key):
                    problems.append(f"{name}.{field}: {key} differs from the spec")
    return problems


def test_spec_is_a_valid_openapi_document() -> None:
    validate(SPEC)
    ops = [
        op["operationId"]
        for item in SPEC["paths"].values()
        for m, op in item.items()
        if m in METHODS
    ]
    assert len(ops) == len(set(ops)) == 18


def test_fastapi_matches_the_spec_for_what_is_implemented() -> None:
    assert drift(app.openapi(), SPEC) == []


def test_drift_check_catches_changes() -> None:
    """The check above must not be vacuous: break a copy of the generated spec four ways."""
    good = app.openapi()
    assert good["paths"] and good["components"]["schemas"]["Health"]

    def broken(edit: Any) -> list[str]:
        gen = yaml.safe_load(yaml.safe_dump(good))
        edit(gen)
        return drift(gen, SPEC)

    health = lambda g: g["components"]["schemas"]["Health"]  # noqa: E731
    assert broken(lambda g: health(g)["properties"].pop("db"))
    assert broken(lambda g: health(g)["properties"].update(extra={"type": "string"}))
    assert broken(lambda g: health(g)["properties"]["status"].update(enum=["ok"]))
    assert broken(lambda g: health(g)["required"].remove("status"))
    assert broken(lambda g: g["paths"].update({"/nope": g["paths"]["/health"]}))
    assert broken(lambda g: g["paths"]["/health"]["get"].update(operationId="other"))
