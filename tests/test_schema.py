"""The mini JSON Schema validator, and the files shipped in the repo against their schemas."""
import json

import pytest

from conftest import GLOBAL, INTAKE, REPO
from lib import schema

S = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name"],
    "$defs": {"hex": {"type": "string", "pattern": "^#[0-9a-f]{6}$"}},
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "mode": {"enum": ["a", "b"]},
        "count": {"type": "integer", "minimum": 1, "maximum": 3},
        "colors": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/hex"}},
        "both": {"allOf": [{"type": "object"}, {"required": ["x"]}]},
    },
}


@pytest.mark.parametrize("data, fragment", [
    ({}, "missing required 'name'"),
    ({"name": ""}, "$.name: must not be empty"),
    ({"name": 5}, "$.name: expected string"),
    ({"name": "n", "typo": 1}, "unknown key 'typo'"),
    ({"name": "n", "mode": "c"}, "is not one of"),
    ({"name": "n", "count": 0}, "below the minimum"),
    ({"name": "n", "count": 9}, "above the maximum"),
    ({"name": "n", "count": True}, "expected integer"),
    ({"name": "n", "colors": []}, "at least 1 item"),
    ({"name": "n", "colors": ["#fff"]}, "$.colors[0]"),
    ({"name": "n", "both": {}}, "$.both: missing required 'x'"),
])
def test_reports_each_kind_of_error_with_its_path(data, fragment):
    errors = schema.validate(data, S)
    assert any(fragment in e for e in errors), errors


def test_valid_data_has_no_errors():
    assert schema.validate({"name": "n", "mode": "a", "count": 2, "colors": ["#aabbcc"], "both": {"x": 1}}, S) == []


def test_reports_all_errors_not_just_the_first():
    assert len(schema.validate({"typo": 1, "mode": "z"}, S)) == 3


def test_ref_into_another_schema_file():
    # product.schema.json points at design.schema.json for the resolved design
    errors = schema.validate({"design": {"name": "x"}}, {"properties": {"design": {"$ref": "design.schema.json#/$defs/resolved"}}})
    assert any("missing required 'mockups'" in e for e in errors)


def test_shipped_files_match_their_schemas():
    example = json.loads((REPO / "design/global.example.json").read_text())
    assert schema.validate(example, *schema.load("design#global")) == []
    template = json.loads((REPO / "assets/_template/design.json").read_text())
    assert schema.validate(template, *schema.load("design#layer")) == []
    assert schema.validate(GLOBAL, *schema.load("design#global")) == []
    assert schema.validate(INTAKE, *schema.load("intake")) == []


def test_global_design_requires_identity_constraints_and_output():
    broken = {"name": "x", "style": {"theme": "t"}}
    errors = schema.validate(broken, *schema.load("design#global"))
    assert any("identity_constraints" in e for e in errors) and any("'output'" in e for e in errors)
