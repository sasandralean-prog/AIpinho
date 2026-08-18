from __future__ import annotations

from aipinho.schemas.pinhoforge_bridge import PinhoForgeBridgeRequest, PinhoForgeBridgeResponse
from aipinho.services.pinhoforge_bridge.pinhoforge_bridge_config_service import PinhoForgeBridgeConfigService
from aipinho.services.pinhoforge_bridge.pinhoforge_bridge_policy_service import PinhoForgeBridgePolicyService
from aipinho.services.pinhoforge_bridge.pinhoforge_manifest_reader import PinhoForgeManifestReader


class PinhoForgeBridgeClient:
    def __init__(
        self,
        *,
        config_service: PinhoForgeBridgeConfigService | None = None,
        manifest_reader: PinhoForgeManifestReader | None = None,
    ) -> None:
        self.config_service = config_service or PinhoForgeBridgeConfigService()
        self.manifest_reader = manifest_reader or PinhoForgeManifestReader()

    def status(self):
        config = self.config_service.runtime()
        status = self.manifest_reader.status(config.manifest_path, provider_id=config.provider_id)
        return status.model_copy(update={
            "allowed_operations": list(config.allowed_operations),
            "blocked_operations": list(config.blocked_operations),
            "execution_enabled": False,
            "mode": "local_authenticated_protocol" if config.transport == "local_protocol" else status.mode,
        })

    def request(self, request: PinhoForgeBridgeRequest) -> PinhoForgeBridgeResponse:
        config = self.config_service.runtime()
        policy = PinhoForgeBridgePolicyService(
            allowed_operations=config.allowed_operations,
            blocked_operations=config.blocked_operations,
            execution_enabled=config.execution_enabled,
        ).evaluate(request.operation)
        if policy.decision == "deny":
            return PinhoForgeBridgeResponse(
                request_id=request.request_id,
                operation=request.operation,
                status="blocked",
                execution_enabled=False,
                policy_decision=policy,
                errors=[policy.reason_code],
            )
        if request.timeout_seconds <= 0:
            return PinhoForgeBridgeResponse(
                request_id=request.request_id,
                operation=request.operation,
                status="timeout",
                execution_enabled=False,
                policy_decision=policy,
                errors=["pinhoforge_bridge_timeout"],
            )
        provider_status = self.status()
        if request.operation == "health":
            return PinhoForgeBridgeResponse(
                request_id=request.request_id,
                operation=request.operation,
                status="ok",
                execution_enabled=False,
                policy_decision=policy,
                payload=provider_status.model_dump(),
                warnings=provider_status.warnings,
                errors=provider_status.errors,
            )
        if request.operation == "handshake":
            return PinhoForgeBridgeResponse(
                request_id=request.request_id,
                operation=request.operation,
                status="ok",
                execution_enabled=False,
                policy_decision=policy,
                payload={
                    "provider_id": config.provider_id,
                    "transport": config.transport,
                    "requires_local_auth": config.require_local_auth,
                    "token_configured": config.token_configured,
                    "allowed_operations": list(config.allowed_operations),
                    "blocked_operations": list(config.blocked_operations),
                },
                warnings=provider_status.warnings,
            )
        if request.operation in {"manifest", "readiness"}:
            return PinhoForgeBridgeResponse(
                request_id=request.request_id,
                operation=request.operation,
                status="ok" if provider_status.manifest_loaded else "invalid_manifest",
                execution_enabled=False,
                policy_decision=policy,
                payload=provider_status.model_dump(),
                warnings=provider_status.warnings,
                errors=provider_status.errors,
            )
        return PinhoForgeBridgeResponse(
            request_id=request.request_id,
            operation=request.operation,
            status="unsupported",
            execution_enabled=False,
            policy_decision=policy,
            errors=["pinhoforge_bridge_operation_unsupported"],
        )
