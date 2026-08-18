from aipinho.schemas.models.inference_runtime_limits import InferenceRuntimeLimits
from aipinho.schemas.models.llama_cpp_config import LlamaCppConfig
from aipinho.schemas.models.llama_cpp_status import LlamaCppStatus
from aipinho.schemas.models.llama_invocation_trace import LlamaInvocationTrace
from aipinho.schemas.models.model_path_validation import ModelPathValidation
from aipinho.schemas.models.model_runtime_estimate import ModelRuntimeEstimate
from aipinho.schemas.models.real_inference_gate import RealInferenceGateDecision


def test_llama_cpp_contract_schemas_dump():
    config = LlamaCppConfig()
    status = LlamaCppStatus()
    decision = RealInferenceGateDecision()
    validation = ModelPathValidation(kind="model")
    estimate = ModelRuntimeEstimate()
    trace = LlamaInvocationTrace()
    limits = InferenceRuntimeLimits()
    assert config.enabled is False
    assert status.status == "disabled"
    assert decision.allowed is False
    assert validation.valid is False
    assert estimate.confidence == "low"
    assert trace.process_started is False
    assert limits.timeout_seconds > 0
