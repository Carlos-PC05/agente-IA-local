"""Tests del registro central de tools (agent/tools/registry.py)."""
from agent.tools import registry


def test_search_documents_esta_registrada():
    tool = registry.get("search_documents")
    assert tool is not None
    assert tool.permission.value == "read"
    assert tool.timeout_seconds == 30.0
