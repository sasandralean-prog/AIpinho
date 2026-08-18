from aipinho.services.models.model_router_service import ModelRouterService


def test_model_router_selects_light_speaker_role_candidate_when_runtime_enabled():
    decision = ModelRouterService().select_model(purpose="chat", role_id="speaker")
    assert decision.status == "ok"
    assert decision.model.model_id == "qwen3_1_7b_q6_k"
    assert decision.provider.provider_id == "llama_cpp_text"
    assert decision.reason == "model_selected"


def test_model_router_uses_role_bindings_for_other_roles_too():
    decision = ModelRouterService().select_model(purpose="debug_trace", role_id="debugger")
    assert decision.status == "ok"
    assert decision.model.model_id == "qwen3_4b_thinking_distill_q4_k_m"
    assert decision.reason == "model_selected"


def test_model_router_keeps_fourteen_b_manual_only_for_auto_selection():
    decision = ModelRouterService().select_model(purpose="planning", role_id="planner", requested_model_id="deepseek_r1_distill_qwen_14b_q4_k_m")
    assert decision.status == "blocked"
    assert decision.reason == "model_manual_only"


def test_model_router_blocks_disabled_real_placeholder():
    decision = ModelRouterService().select_model(requested_model_id="llama.local.placeholder", purpose="chat", role_id="speaker")
    assert decision.status == "blocked"
    assert decision.reason in {"model_disabled", "provider_disabled", "model_capability_or_role_mismatch"}


def test_model_router_respects_explicit_stub_request_over_role_binding():
    decision = ModelRouterService().select_model(requested_model_id="stub.default", purpose="project_report", role_id="reporter")
    assert decision.status == "ok"
    assert decision.model.model_id == "stub.default"
    assert decision.provider.provider_id == "stub.local"
