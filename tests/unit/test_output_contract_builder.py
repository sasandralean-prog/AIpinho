from aipinho.services.prompts.output_contract_builder import OutputContractBuilder


def test_output_contract_builder_validates_json_findings():
    builder = OutputContractBuilder()
    contract = builder.get_contract("json_findings")
    ok = builder.validate_model_response_against_contract('{"findings": [], "limitations": []}', contract)
    bad = builder.validate_model_response_against_contract('{"findings": []}', contract)
    assert ok["valid"] is True
    assert bad["valid"] is False


def test_output_contract_builder_chat_response_accepts_nonempty_text():
    builder = OutputContractBuilder()
    contract = builder.get_contract("chat_response")
    assert builder.validate_model_response_against_contract("ok", contract)["valid"] is True
