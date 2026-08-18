from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.external_gateway import GatewayClientType, GatewayResponse


PublicOperation = Literal["chat", "execute", "analyze", "doctor", "validate", "artifacts"]


class PublicContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"public_contract_{uuid4().hex}")
    operation: PublicOperation
    version: str = "1.0"
    contract_type: str
    target_module: str
    schema_ref: str
    gateway_required: bool = True
    kernel_required: bool = True


class PublicRuntimeRequest(AIpinhoModel):
    client_id: str = "public_client"
    client_type: GatewayClientType = "rest"
    api_version: str = "1.0"
    operation: PublicOperation
    contract: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicRuntimeResponse(AIpinhoModel):
    public_response_id: str = Field(default_factory=lambda: f"public_response_{uuid4().hex}")
    operation: PublicOperation
    api_version: str
    status: str
    gateway_response: GatewayResponse
    runtime_result: dict[str, Any] = Field(default_factory=dict)
    task_id: str | None = None
    task_run_id: str | None = None
    operation_id: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    validation_state: dict[str, Any] = Field(default_factory=dict)
    completion_state: dict[str, Any] = Field(default_factory=dict)
    speaker_truth_state: dict[str, Any] = Field(default_factory=dict)
    audit_id: str = Field(default_factory=lambda: f"api_audit_{uuid4().hex}")
    telemetry_recorded: bool = True
    public_contract_version: str = "1.0"
    gateway_required: bool = True
    kernel_required: bool = True
    deterministic: bool = True
    mutates_runtime: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PublicContractRegistry(AIpinhoModel):
    version: str = "1.0"
    contracts: list[PublicContract] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False


class ApiAudit(AIpinhoModel):
    audit_id: str = Field(default_factory=lambda: f"api_audit_{uuid4().hex}")
    operation: PublicOperation
    client_id: str
    client_type: GatewayClientType
    status: str
    gateway_response_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    deterministic: bool = True
    mutates_runtime: bool = False


class PublicApiHistory(AIpinhoModel):
    count: int
    audits: list[ApiAudit] = Field(default_factory=list)
    deterministic: bool = True
    mutates_runtime: bool = False
