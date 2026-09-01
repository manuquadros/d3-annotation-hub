"""The OpenAPI schema is the contract a frontend client is generated from.

These pin the properties such a generator depends on: the annotation models are
described rather than passed through as opaque strings, no endpoint answers with
an unnamed object, and operation ids are unique so generated call sites keep
their names.
"""

import json

import pytest

from ahbackend.api.api import app
from ahbackend.openapi import render


@pytest.fixture(scope="module")
def schema() -> dict:
    return app.openapi()


def _json_response_schema(operation: dict) -> dict | None:
    ok = operation.get("responses", {}).get("200", {})
    return ok.get("content", {}).get("application/json", {}).get("schema")


class TestAnnotationContract:
    def test_annotation_models_are_described(self, schema):
        components = schema["components"]["schemas"]
        for name in (
            "ReferenceAnnotation",
            "EntityAnnotation",
            "Pointer",
            "Relation",
            "Reference",
        ):
            assert name in components

    def test_reference_returns_the_annotation_model(self, schema):
        body = _json_response_schema(schema["paths"]["/reference/"]["get"])
        assert body == {"$ref": "#/components/schemas/ReferenceAnnotation"}

    def test_save_accepts_the_annotation_model(self, schema):
        request = schema["paths"]["/save/"]["post"]["requestBody"]
        assert request["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ReferenceAnnotation"
        }


class TestSchemaShape:
    def test_no_endpoint_answers_with_an_unnamed_object(self, schema):
        """A bare ``-> dict`` generates as ``Record<string, unknown>``."""
        untyped = [
            f"{method.upper()} {path}"
            for path, methods in schema["paths"].items()
            for method, operation in methods.items()
            if (found := _json_response_schema(operation)) is not None
            and found.get("additionalProperties") is True
        ]
        assert untyped == []

    def test_operation_ids_are_unique(self, schema):
        ids = [
            operation["operationId"]
            for methods in schema["paths"].values()
            for operation in methods.values()
            if "operationId" in operation
        ]
        assert len(ids) == len(set(ids))

    def test_operation_ids_are_the_endpoint_names(self, schema):
        assert (
            schema["paths"]["/reference/"]["get"]["operationId"]
            == "fetch_annotation"
        )


class TestExport:
    def test_render_emits_stable_parseable_json(self):
        first = render()
        assert json.loads(first)["openapi"].startswith("3.")
        assert render() == first
