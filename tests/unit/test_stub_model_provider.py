import json

from aipinho.adapters.llm_providers.stub_provider import StubProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_message import PromptMessage


def test_stub_model_provider_is_deterministic_and_not_real_inference():
    request = ModelRequest(model_id="stub.default", provider_id="stub.local", messages=[PromptMessage(role="user", content="Ola")])
    first = StubProvider().invoke(request)
    second = StubProvider().invoke(request)
    assert first.content == second.content
    assert first.real_inference is False
    assert "stub_model_used" in first.warnings


def test_stub_model_provider_can_emit_json_findings_contract():
    request = ModelRequest(
        model_id="stub.default",
        provider_id="stub.local",
        messages=[PromptMessage(role="user", content="Findings")],
        output_contract={"contract_type": "json_findings"},
    )
    response = StubProvider().invoke(request)
    parsed = json.loads(response.content)
    assert parsed["findings"] == []
    assert parsed["limitations"]


def test_stub_model_provider_markdown_report_includes_evidence_refs():
    request = ModelRequest(
        model_id="stub.default",
        provider_id="stub.local",
        messages=[PromptMessage(role="user", content="Report")],
        output_contract={"contract_type": "markdown_report", "require_evidence": True},
        metadata={"evidence_context": [{"evidence_id": "ev_readme", "source": "README.md"}]},
    )

    response = StubProvider().invoke(request)

    assert "# Evidence" in response.content
    assert "ev_readme" in response.content
