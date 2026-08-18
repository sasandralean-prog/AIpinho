from aipinho.schemas.roles.role_model_binding import RoleInferenceResult, RoleModelRun
from aipinho.services.roles.role_model_run_store import RoleModelRunStore


def test_role_model_run_store_roundtrip(tmp_path):
    store = RoleModelRunStore(store_dir=tmp_path)
    result = RoleInferenceResult(role_id="coder", status="fallback_used", selected_model_id="qwen2_5_coder_7b_q4_k_m")

    store.save(RoleModelRun(result=result, request={"prompt": "test"}, prompt_contract={"contract": "coder_output"}))

    loaded = store.get(result.run_id)
    assert loaded is not None
    assert loaded.result.role_id == "coder"
    assert store.list_runs(role_id="coder")[0].run_id == result.run_id
