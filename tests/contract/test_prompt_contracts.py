from aipinho.schemas.prompts.output_contract import OutputContract
from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem, PromptContextSafety
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.prompts.safety_envelope import SafetyEnvelope


def test_prompt_assembly_request_defaults_to_stub_model():
    request = PromptAssemblyRequest(purpose="chat", role_id="speaker", user_message="Ola")
    assert request.model_id == "stub.default"
    assert request.output_contract_type == "plain_text"


def test_prompt_context_item_carries_safety_metadata():
    item = PromptContextItem(source_type="file", title="secret", content="token", safety=PromptContextSafety(blocked=True, reason="secret"))
    assert item.safety.blocked is True
    assert item.safety.reason == "secret"


def test_prompt_contract_core_schemas_dump():
    message = PromptMessage(role="system", content="rules")
    contract = OutputContract(contract_type="json_findings", format="json", required_fields=["findings"])
    envelope = SafetyEnvelope(envelope_id="safety_test", purpose="chat", rules=["no raw"], real_inference=False)
    assert message.model_dump()["role"] == "system"
    assert contract.model_dump()["required_fields"] == ["findings"]
    assert envelope.model_dump()["real_inference"] is False

