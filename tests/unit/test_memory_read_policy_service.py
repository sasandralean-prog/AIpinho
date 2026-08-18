from aipinho.services.memory.memory_read_policy_service import MemoryReadPolicyService


def test_memory_read_policy_service_disables_auto_prompt_injection():
    status = MemoryReadPolicyService().status()
    assert status["prompt_assembly_auto_injection"] is False
    assert status["chat_auto_injection"] is False
    assert status["explicit_read_allowed"] is True
