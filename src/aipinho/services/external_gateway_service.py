from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.external_gateway import GatewayContext, GatewayHistory, GatewayPolicy, GatewayRequest, GatewayResponse, GatewaySession, GatewaySessionRequest
from aipinho.services.runtime.runtime_kernel_service import RuntimeKernel


class ExternalGateway:
    _sessions: dict[str, GatewaySession] = {}
    _responses: list[GatewayResponse] = []

    def __init__(self, policy: GatewayPolicy | None = None, kernel: RuntimeKernel | None = None) -> None:
        self.policy = policy or GatewayPolicy()
        self.kernel = kernel or RuntimeKernel()

    def create_session(self, request: GatewaySessionRequest) -> GatewaySession:
        reasons = self._validate_client(request.client_type, request.version)
        status = "blocked" if reasons else "active"
        session = GatewaySession(
            client_id=request.client_id,
            client_type=request.client_type,
            version=request.version,
            status=status,
            metadata={**request.metadata, "reason_codes": reasons},
        )
        self._sessions[session.gateway_session_id] = session
        return session

    def handle(self, request: GatewayRequest) -> GatewayResponse:
        context = GatewayContext(client_id=request.client_id, client_type=request.client_type, version=request.version, metadata=request.metadata)
        reasons = self._validate_client(request.client_type, request.version)
        reasons.extend(self._validate_contract(request.contract))
        if request.target_module in self.policy.forbidden_targets:
            reasons.append("direct_internal_module_access_forbidden")
        session = self._session(request)
        if session and session.status != "active":
            reasons.append("gateway_session_not_active")
        if reasons:
            return self._store(
                GatewayResponse(
                    status="blocked",
                    gateway_session_id=session.gateway_session_id if session else None,
                    context=context,
                    reason_codes=list(dict.fromkeys(reasons)),
                    kernel_status="not_dispatched",
                )
            )

        self.kernel.boot()
        kernel_result = self.kernel.dispatch(request.target_module, contract=request.contract)
        status = "accepted" if kernel_result.get("status") == "ready" else "blocked"
        reasons = [] if status == "accepted" else [str(kernel_result.get("reason") or "kernel_dispatch_blocked")]
        return self._store(
            GatewayResponse(
                status=status,
                gateway_session_id=session.gateway_session_id if session else None,
                context=context,
                kernel_status=str(kernel_result.get("status")),
                kernel_result=kernel_result,
                reason_codes=reasons,
            )
        )

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "external_gateway",
            "sessions": len(self._sessions),
            "responses": len(self._responses),
            "supported_versions": self.policy.supported_versions,
            "deterministic": True,
            "mutates_runtime": False,
        }

    def version(self) -> dict[str, object]:
        return {"gateway": "1.0", "contract": "external_gateway.v1", "supported_versions": self.policy.supported_versions}

    def history(self) -> GatewayHistory:
        return GatewayHistory(count=len(self._responses), responses=list(self._responses))

    def _validate_client(self, client_type: str, version: str) -> list[str]:
        reasons: list[str] = []
        if client_type not in self.policy.allowed_client_types:
            reasons.append("client_type_not_allowed")
        if version not in self.policy.supported_versions:
            reasons.append("gateway_version_not_supported")
        return reasons

    def _validate_contract(self, contract: dict[str, object]) -> list[str]:
        reasons: list[str] = []
        for key in self.policy.required_contract_keys:
            if key not in contract:
                reasons.append(f"contract_key_missing:{key}")
        return reasons

    def _session(self, request: GatewayRequest) -> GatewaySession | None:
        if request.session_id and request.session_id in self._sessions:
            return self._sessions[request.session_id]
        session = GatewaySession(client_id=request.client_id, client_type=request.client_type, version=request.version, updated_at=datetime.now(timezone.utc).isoformat())
        self._sessions[session.gateway_session_id] = session
        return session

    def _store(self, response: GatewayResponse) -> GatewayResponse:
        self._responses.append(response)
        return response
