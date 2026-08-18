from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from starlette.responses import FileResponse

from aipinho.schemas.codex_agent import CodexAgentRequest
from aipinho.schemas.codex_governed_execution import (
    CodexGovernedContractRequest,
    CodexGovernedProposalRequest,
)
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.services.codex_agent import CodexAgentService
from aipinho.services.codex_agent.codex_governed_execution_service import (
    CodexGovernedExecutionService,
)
from aipinho.services.security.local_token_service import LocalTokenService

router = APIRouter(prefix="/api/v1/codex-agent", tags=["codex-agent"])


class CreateCodexSessionRequest(AIpinhoModel):
    title: str = "Codex Agent"


class RenameCodexSessionRequest(AIpinhoModel):
    title: str


class CodexApprovalRequest(AIpinhoModel):
    operation_id: str | None = None


@router.get("/health")
def health() -> dict[str, object]:
    return CodexAgentService().health()


@router.get("/config/status")
def config_status() -> dict[str, object]:
    return {"status": "ok", "config": CodexAgentService().config_service.status().model_dump()}


@router.get("/governed/status")
def governed_status() -> dict[str, object]:
    return {"status": "ok", "governed_execution": CodexGovernedExecutionService().status()}


@router.post("/sessions")
def create_session(request: CreateCodexSessionRequest | None = None) -> dict[str, object]:
    session = CodexAgentService().create_session(request.title if request else "Codex Agent")
    return {"status": "ok", "session": session.model_dump()}


@router.get("/sessions")
def list_sessions() -> dict[str, object]:
    sessions = CodexAgentService().sessions()
    return {"status": "ok", "sessions": [session.model_dump() for session in sessions], "total": len(sessions)}


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, object]:
    session = CodexAgentService().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.post("/sessions/{session_id}/rename")
def rename_session(session_id: str, request: RenameCodexSessionRequest) -> dict[str, object]:
    session = CodexAgentService().rename_session(session_id, request.title)
    if session is None:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    return {"status": "ok", "session": session.model_dump()}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, object]:
    deleted = CodexAgentService().delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    return {"status": "ok", "deleted": True, "session_id": session_id}


@router.post("/sessions/{session_id}/delete")
def delete_session_post(session_id: str) -> dict[str, object]:
    return delete_session(session_id)


@router.get("/sessions/{session_id}/messages")
def messages(session_id: str, after_message_id: str | None = Query(default=None)) -> dict[str, object]:
    try:
        items = CodexAgentService().messages_after(session_id, after_message_id=after_message_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc
    return {"status": "ok", "messages": [item.model_dump() for item in items]}


@router.get("/sessions/{session_id}/view-model")
def view_model(
    session_id: str,
    after_event_id: str | None = Query(default=None),
) -> dict[str, object]:
    try:
        return CodexAgentService().mobile_view_model(
            session_id,
            after_event_id=after_event_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc


@router.post("/sessions/{session_id}/send")
def send(session_id: str, request: CodexAgentRequest) -> dict[str, object]:
    try:
        response = CodexAgentService().send(request.model_copy(update={"session_id": session_id}))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc
    return {"status": "ok", "response": response.model_dump()}


@router.get("/sessions/{session_id}/runs")
def session_runs(session_id: str) -> dict[str, object]:
    if CodexAgentService().get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    runs = CodexAgentService().runs(session_id)
    return {"status": "ok", "runs": [run.model_dump() for run in runs]}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    run = CodexAgentService().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="codex_run_not_found")
    return {"status": "ok", "run": run.model_dump()}


@router.get("/runs/{run_id}/events")
def run_events(run_id: str, after_event_id: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500)) -> dict[str, object]:
    if CodexAgentService().get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="codex_run_not_found")
    events = CodexAgentService().events(run_id, after_event_id=after_event_id, limit=limit)
    return {"status": "ok", "events": [event.model_dump() for event in events], "after_event_id": after_event_id}


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, object]:
    try:
        return CodexAgentService().cancel_run(run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_run_not_found") from exc


@router.post("/sessions/{session_id}/plan")
def plan(session_id: str, request: CodexAgentRequest) -> dict[str, object]:
    planned = request.model_copy(update={"session_id": session_id, "operation_type": "codex_plan"})
    return send(session_id, planned)


@router.post("/sessions/{session_id}/preview")
def preview(session_id: str, request: CodexAgentRequest) -> dict[str, object]:
    preview_request = request.model_copy(
        update={
            "session_id": session_id,
            "operation_type": "codex_patch_preview",
            "requested_capabilities": sorted(set(request.requested_capabilities + ["create_patch_preview"])),
        }
    )
    return send(session_id, preview_request)


@router.post("/sessions/{session_id}/contracts/propose")
def propose_governed_contract(
    session_id: str, request: CodexGovernedProposalRequest
) -> dict[str, object]:
    if CodexAgentService().get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    try:
        contract = CodexGovernedExecutionService().propose_contract(
            request.model_copy(update={"session_id": session_id})
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    service = CodexGovernedExecutionService()
    return {"status": contract.status, "contract": service.public_contract(contract)}


@router.post("/sessions/{session_id}/contracts")
def create_governed_contract(
    session_id: str, request: CodexGovernedContractRequest
) -> dict[str, object]:
    if CodexAgentService().get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    try:
        contract = CodexGovernedExecutionService().create_contract(
            request.model_copy(update={"session_id": session_id})
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    service = CodexGovernedExecutionService()
    return {"status": contract.status, "contract": service.public_contract(contract)}


@router.get("/sessions/{session_id}/contracts")
def list_governed_contracts(session_id: str) -> dict[str, object]:
    if CodexAgentService().get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    contracts = CodexGovernedExecutionService().list(session_id=session_id)
    service = CodexGovernedExecutionService()
    return {
        "status": "ok",
        "contracts": [service.public_contract(contract) for contract in contracts],
        "total": len(contracts),
    }


@router.get("/contracts/{contract_id}")
def get_governed_contract(
    contract_id: str, include_content: bool = Query(default=False)
) -> dict[str, object]:
    service = CodexGovernedExecutionService()
    contract = service.get(contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="codex_contract_not_found")
    return {
        "status": contract.status,
        "contract": service.public_contract(
            contract, include_content=include_content
        ),
    }


@router.post("/contracts/{contract_id}/request-approval")
def request_governed_contract_approval(contract_id: str) -> dict[str, object]:
    try:
        decision = CodexGovernedExecutionService().request_approval(contract_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_contract_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    service = CodexGovernedExecutionService()
    payload = decision.model_dump()
    payload["contract"] = service.public_contract(decision.contract)
    return payload


@router.post("/contracts/{contract_id}/refresh-approvals")
def refresh_governed_contract_approvals(contract_id: str) -> dict[str, object]:
    try:
        contract = CodexGovernedExecutionService().refresh_approval_state(contract_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_contract_not_found") from exc
    service = CodexGovernedExecutionService()
    return {"status": contract.status, "contract": service.public_contract(contract)}


@router.post("/contracts/{contract_id}/execute")
def execute_governed_contract(contract_id: str) -> dict[str, object]:
    try:
        contract = CodexGovernedExecutionService().execute(contract_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_contract_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    service = CodexGovernedExecutionService()
    return {"status": contract.status, "contract": service.public_contract(contract)}


@router.post("/contracts/{contract_id}/cancel")
def cancel_governed_contract(contract_id: str) -> dict[str, object]:
    try:
        contract = CodexGovernedExecutionService().cancel(contract_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_contract_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    service = CodexGovernedExecutionService()
    return {"status": contract.status, "contract": service.public_contract(contract)}


@router.post("/sessions/{session_id}/request-approval")
def request_approval(session_id: str, request: CodexApprovalRequest | None = None) -> dict[str, object]:
    try:
        return CodexAgentService().guarded_action(session_id, f"request_approval:{request.operation_id if request else ''}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc


@router.post("/sessions/{session_id}/apply-approved")
def apply_approved(session_id: str) -> dict[str, object]:
    try:
        return CodexAgentService().guarded_action(session_id, "apply_approved_patch")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc


@router.post("/sessions/{session_id}/run-approved-shell")
def run_approved_shell(session_id: str) -> dict[str, object]:
    try:
        return CodexAgentService().guarded_action(session_id, "run_approved_shell")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc


@router.get("/sessions/{session_id}/artifacts")
def artifacts(session_id: str) -> dict[str, object]:
    try:
        items = CodexAgentService().artifacts(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found")
    return {"status": "ok", "session_id": session_id, "artifacts": [item.model_dump() for item in items]}


def _parse_multipart_upload(body: bytes, content_type: str) -> tuple[str, bytes, str]:
    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    for part in message.iter_parts():
        if part.get_param("name", header="content-disposition") != "file":
            continue
        filename = part.get_filename() or "upload.bin"
        payload = part.get_payload(decode=True) or b""
        part_type = part.get_content_type() or "application/octet-stream"
        return Path(filename).name, payload, part_type
    raise ValueError("multipart_file_part_missing")


@router.post("/sessions/{session_id}/artifacts/upload")
async def upload_artifact(session_id: str, request: Request, authorization: str | None = Header(default=None), run_id: str | None = Query(default=None)) -> dict[str, object]:
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type.lower():
        raise HTTPException(status_code=415, detail="multipart_form_data_required")
    try:
        filename, content, part_type = _parse_multipart_upload(await request.body(), content_type)
        artifact = CodexAgentService().attach_uploaded_artifact(session_id=session_id, filename=filename, content=content, content_type=part_type, run_id=run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="codex_session_not_found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "ok", "artifact": artifact.model_dump(), "download_endpoint": artifact.download_endpoint, "requires_token": True}


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str, authorization: str | None = Header(default=None)):
    if not LocalTokenService().validate_authorization(authorization):
        raise HTTPException(status_code=401, detail="local_token_required")
    try:
        path = CodexAgentService().artifact_download_path(artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="artifact_not_found") from exc
    return FileResponse(path, filename=path.name)
