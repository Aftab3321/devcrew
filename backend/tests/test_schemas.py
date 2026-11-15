import httpx
import pytest
from openai.lib._pydantic import to_strict_json_schema
from devcrew_backend.services.registry import REGISTRY
from devcrew_backend.services.models import Plan
from devcrew_backend.services.errors import provider_error
from devcrew_backend.services.limits import RequestMonitor
from devcrew_backend.services.storage import Session


# Recursively verify each object schema against the provider contract.
def assert_strict_objects(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, node
            assert set(node.get("required", [])) == set(
                node.get("properties", {})
            ), node
        for value in node.values():
            assert_strict_objects(value)
    elif isinstance(node, list):
        for value in node:
            assert_strict_objects(value)


# Verify that all agent schemas meet provider strict object requirements.
@pytest.mark.parametrize("schema", list({c.schema for c in REGISTRY.values()}))
def test_all_agent_schemas_meet_provider_strict_object_requirements(schema):
    assert_strict_objects(to_strict_json_schema(schema))


# Verify that selection reasons is fixed shape not arbitrary dictionary.
def test_selection_reasons_is_fixed_shape_not_arbitrary_dictionary():
    schema = to_strict_json_schema(Plan)
    reasons = schema["$defs"]["SelectionReasons"]
    assert set(reasons["properties"]) == {"designer", "standards", "security"}
    assert reasons["additionalProperties"] is False


# Verify that actionable schema rejection is persisted safely.
def test_actionable_schema_rejection_is_persisted_safely(tmp_path):
    session = Session(tmp_path, "test", "test")
    monitor = RequestMonitor(session)
    monitor.begin("planner")
    body = {
        "error": {
            "message": "Invalid schema for response_format 'Plan': invalid required keys sk-secret-key",
            "param": "response_format",
            "type": "invalid_request_error",
        }
    }
    request = httpx.Request(
        "POST",
        "https://provider.invalid",
        headers={"Authorization": "Bearer topsecret"},
    )
    monitor.after_response("planner", httpx.Response(400, request=request, json=body))
    saved = (session.path / "provider_error.json").read_text()
    assert "Structured-output schema rejected" in saved
    assert "response_format" in saved
    assert "topsecret" not in saved
    assert "sk-secret-key" not in saved


# Verify that unrelated error does not echo private request content.
def test_unrelated_error_does_not_echo_private_request_content():
    error = provider_error(
        400,
        {
            "error": {
                "message": "Private content from user input",
                "param": "max_tokens",
            }
        },
    )
    assert "max_tokens" in error["message"]
    assert "Private" not in error["message"]
