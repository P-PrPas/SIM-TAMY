"""docs/openapi.yaml is the contract (API_DESIGN 13); FastAPI's spec may not drift from it.

Incremental by design: only what the backend implements is compared, so this tightens itself as
endpoints land (T-040+). For every implemented operation it checks the method, operationId, path and
query parameters, the request body and every response schema the code declares (referenced schema
names and shapes, so renaming a component or changing a payload to another type is drift), and that
the spec's 2xx responses still exist. For every schema name present in both it checks property
names, shapes, and that anything the spec requires is required in code.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate

from app.main import app

SPEC: dict[str, Any] = yaml.safe_load(
    (Path(__file__).resolve().parents[4] / "docs" / "openapi.yaml").read_text(encoding="utf-8")
)
METHODS = {"get", "post", "put", "patch", "delete"}
Doc = dict[str, Any]


def _ref(doc: Doc, node: Doc) -> Doc:
    while "$ref" in node:
        target: Any = doc
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def describe(node: Doc) -> Any:
    """Comparable shape of a schema: ref name, or type/format/enum, recursing into arrays/objects.

    Null alternatives are dropped so FastAPI's `anyOf [X, null]` equals the spec's `nullable`.
    """
    if "$ref" in node:
        return ("ref", node["$ref"].rsplit("/", 1)[-1])
    alts = node.get("anyOf") or node.get("oneOf")
    if alts:
        shapes = [describe(a) for a in alts if a.get("type") != "null"]
        return shapes[0] if len(shapes) == 1 else ("any", sorted(map(repr, shapes)))
    kind = node.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), None)
    shape: Doc = {"type": kind, "format": node.get("format"), "enum": node.get("enum")}
    if kind == "array" and "items" in node:
        shape["items"] = describe(node["items"])
    if kind == "object" and "properties" in node:
        shape["properties"] = {k: describe(v) for k, v in sorted(node["properties"].items())}
    return shape


def _json_schema(holder: Doc | None) -> Any:
    schema = ((holder or {}).get("content") or {}).get("application/json", {}).get("schema")
    return None if schema is None else describe(schema)


def _params(doc: Doc, item: Doc, op: Doc) -> set[tuple[str, str]]:
    found = [_ref(doc, p) for p in [*item.get("parameters", []), *op.get("parameters", [])]]
    return {(p["name"], p["in"]) for p in found if p["in"] in ("path", "query")}


def _operation_drift(
    label: str, gen: tuple[Doc, Doc, Doc], spec: tuple[Doc, Doc, Doc]
) -> list[str]:
    """Each side is (document, path item, operation)."""
    (gdoc, gitem, gop), (sdoc, sitem, sop) = gen, spec
    problems: list[str] = []
    if gop.get("operationId") != sop.get("operationId"):
        problems.append(f"{label}: operationId differs from the spec")
    if _params(gdoc, gitem, gop) != _params(sdoc, sitem, sop):
        problems.append(f"{label}: path/query parameters differ from the spec")
    if _json_schema(gop.get("requestBody")) != _json_schema(sop.get("requestBody")):
        problems.append(f"{label}: request body differs from the spec")
    gen_responses, spec_responses = gop.get("responses", {}), sop.get("responses", {})
    for code, response in gen_responses.items():
        if code not in spec_responses:
            problems.append(f"{label}: response {code} is not in the spec")
        elif _json_schema(response) != _json_schema(spec_responses[code]):
            problems.append(f"{label}: response {code} differs from the spec")
    problems += [
        f"{label}: spec response {code} is missing in code"
        for code in spec_responses
        if code.startswith("2") and code not in gen_responses
    ]
    return problems


def _flatten(doc: Doc, schema: Doc) -> Doc:
    """Merge `allOf` parts (the spec's CaseBrief) into one properties/required view."""
    merged: Doc = {"properties": {}, "required": []}
    for part in schema.get("allOf", [schema]):
        part = _flatten(doc, _ref(doc, part)) if "allOf" in part or "$ref" in part else part
        merged["properties"].update(part.get("properties", {}))
        merged["required"] += part.get("required", [])
    if "allOf" not in schema:
        merged["properties"].update(schema.get("properties", {}))
        merged["required"] += schema.get("required", [])
    return merged


def drift(generated: Doc, spec: Doc) -> list[str]:
    problems: list[str] = []
    for path, gitem in generated["paths"].items():
        if path not in spec["paths"]:
            problems.append(f"path {path} is not in the spec")
            continue
        sitem = spec["paths"][path]
        for method in METHODS & set(gitem):
            label = f"{method.upper()} {path}"
            if method not in sitem:
                problems.append(f"{label} is not in the spec")
                continue
            problems += _operation_drift(
                label, (generated, gitem, gitem[method]), (spec, sitem, sitem[method])
            )

    spec_schemas = spec["components"]["schemas"]
    for name, raw in generated.get("components", {}).get("schemas", {}).items():
        if name not in spec_schemas:
            continue  # FastAPI helper schemas (HTTPValidationError, ...)
        schema, want = _flatten(generated, raw), _flatten(spec, spec_schemas[name])
        props, want_props = schema.get("properties", {}), want.get("properties", {})
        if set(props) != set(want_props):
            problems.append(f"{name}: properties {sorted(props)} != spec {sorted(want_props)}")
        if not set(want.get("required", [])) <= set(schema.get("required", [])):
            problems.append(f"{name}: a field the spec requires is optional in code")
        problems += [
            f"{name}.{field}: differs from the spec"
            for field in set(props) & set(want_props)
            if describe(props[field]) != describe(want_props[field])
        ]
    return problems


def test_spec_is_a_valid_openapi_document() -> None:
    validate(SPEC)
    ops = [
        op["operationId"]
        for item in SPEC["paths"].values()
        for m, op in item.items()
        if m in METHODS
    ]
    assert len(ops) == len(set(ops)) == 26


def test_fastapi_matches_the_spec_for_what_is_implemented() -> None:
    assert drift(app.openapi(), SPEC) == []


def test_the_checker_accepts_the_whole_spec_compared_with_itself() -> None:
    """Sanity: it handles all 18 operations (refs, bodies, params) without false positives."""
    assert drift(SPEC, SPEC) == []


def _copy(doc: Doc) -> Doc:
    return yaml.safe_load(yaml.safe_dump(doc))


def _health(g: Doc) -> Doc:
    return g["components"]["schemas"]["Health"]


def _get_health(g: Doc) -> Doc:
    return g["paths"]["/health"]["get"]


def _json(op: Doc, code: str) -> Doc:
    return op["responses"][code]["content"]["application/json"]


def _rename_health(g: Doc) -> None:
    g["components"]["schemas"]["HealthStatus"] = g["components"]["schemas"].pop("Health")
    _json(_get_health(g), "200")["schema"] = {"$ref": "#/components/schemas/HealthStatus"}


def _response_becomes_array(g: Doc) -> None:
    ref = {"$ref": "#/components/schemas/Health"}
    _json(_get_health(g), "200")["schema"] = {"type": "array", "items": ref}


def _undeclared_response_code(g: Doc) -> None:
    _get_health(g)["responses"]["404"] = _get_health(g)["responses"]["200"]


def _unexpected_query_param(g: Doc) -> None:
    _get_health(g)["parameters"] = [{"name": "q", "in": "query", "schema": {"type": "string"}}]


def _unexpected_request_body(g: Doc) -> None:
    body = {"content": {"application/json": {"schema": {"type": "object"}}}}
    _get_health(g)["requestBody"] = body


GENERATED_BREAKS: dict[str, Callable[[Doc], object]] = {
    "drop_property": lambda g: _health(g)["properties"].pop("db"),
    "add_property": lambda g: _health(g)["properties"].update(extra={"type": "string"}),
    "narrow_enum": lambda g: _health(g)["properties"]["status"].update(enum=["ok"]),
    "property_type": lambda g: _health(g)["properties"]["cases_loaded"].update(type="string"),
    "relax_required": lambda g: _health(g)["required"].remove("status"),
    "extra_path": lambda g: g["paths"].update({"/nope": g["paths"]["/health"]}),
    "operation_id": lambda g: _get_health(g).update(operationId="other"),
    "rename_schema": _rename_health,
    "response_becomes_integer": lambda g: _json(_get_health(g), "200").update(
        schema={"type": "integer"}
    ),
    "response_becomes_array": _response_becomes_array,
    "undeclared_response_code": _undeclared_response_code,
    "success_response_removed": lambda g: _get_health(g)["responses"].pop("200"),
    "unexpected_query_param": _unexpected_query_param,
    "unexpected_request_body": _unexpected_request_body,
}


def test_drift_check_catches_every_kind_of_breakage_on_what_is_implemented() -> None:
    good = app.openapi()
    assert good["paths"] and drift(good, SPEC) == []
    for name, edit in GENERATED_BREAKS.items():
        broken = _copy(good)
        edit(broken)
        assert drift(broken, SPEC), f"drift not detected: {name}"


def _turn(d: Doc) -> Doc:
    return d["paths"]["/v1/sessions/{session_id}/turns"]["post"]


def _decision(d: Doc) -> Doc:
    return d["paths"]["/v1/sessions/{session_id}/decision"]["post"]


def _body(op: Doc) -> Doc:
    return op["requestBody"]["content"]["application/json"]


SPEC_BREAKS: dict[str, Callable[[Doc], object]] = {
    "request_body_type": lambda g: _body(_turn(g)).update(schema={"type": "string"}),
    "request_body_ref": lambda g: _body(_decision(g)).update(
        schema={"$ref": "#/components/schemas/Health"}
    ),
    "parameters_removed": lambda g: _turn(g).update(parameters=[]),
    "response_type": lambda g: _json(_decision(g), "200").update(schema={"type": "integer"}),
}


def test_drift_check_catches_breakage_on_operations_not_implemented_yet() -> None:
    """Break a copy of the spec itself, so requests/params of all 18 operations are covered."""
    for name, edit in SPEC_BREAKS.items():
        broken = _copy(SPEC)
        edit(broken)
        assert drift(broken, SPEC), f"drift not detected: {name}"
