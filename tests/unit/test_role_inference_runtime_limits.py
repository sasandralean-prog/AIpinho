from aipinho.schemas.models.model_response import ModelResponse
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.roles.role_inference_service import RoleInferenceService


class CapturingInvoker:
    def __init__(self) -> None:
        self.request = None

    def invoke_role_model(self, request):
        self.request = request
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="completed",
            content='{"replacement":"ok"}',
            real_inference=True,
        )


def test_role_inference_respects_request_runtime_limits():
    invoker = CapturingInvoker()
    result = RoleInferenceService(invoker=invoker).run(
        "patch_planner",
        RoleInferenceRequest(
            role_id="patch_planner",
            prompt="Return a replacement only.",
            metadata={
                "max_output_tokens": 64,
                "timeout_seconds": 30,
                "ctx_size": 2048,
            },
        ),
    )

    assert result.status == "completed"
    assert invoker.request is not None
    assert invoker.request.generation_config.max_tokens == 64
    assert invoker.request.metadata["timeout_seconds"] == 30
    assert invoker.request.metadata["ctx_size"] == 2048
