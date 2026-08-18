from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.maintenance.contracts import (
    DiagnosisConfidence,
    DiagnosisEvidence,
    DiagnosisFinding,
    DiagnosisRequest,
    DiagnosisResult,
    MaintenanceRun,
    RepairProposalRequest,
)
from aipinho.services.maintenance.maintenance_core import MaintenanceRunService, RepairProposalService


def evidence(source_id: str | None = None) -> dict[str, object]:
    identifier = source_id or f"event_{uuid4().hex}"
    return {
        "source_type": "event_summary",
        "source_id": identifier,
        "summary": "Structured maintenance evidence.",
        "details": {"state": "observed"},
        "confidence": 0.95,
        "event_ref": identifier,
    }


def diagnosis_payload(signals: dict[str, object] | None = None) -> dict[str, object]:
    item = evidence()
    return {
        "reason": "Evaluate structured maintenance signals.",
        "scope": {"task_id": f"task_{uuid4().hex}"},
        "evidence": [item],
        "signals": signals or {},
    }


def create_diagnosis(client, signals: dict[str, object] | None = None) -> dict[str, object]:
    response = client.post("/api/v1/maintenance/diagnose", json=diagnosis_payload(signals))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed", body
    return body["run"]


def create_proposal(client, repair_type: str = "patch_plan_preview") -> dict[str, object]:
    run = create_diagnosis(
        client,
        {"requires_patch": True, "read_only": True, "source_refs": ["event_contract"]},
    )
    response = client.post(
        "/api/v1/maintenance/repair/propose",
        json={
            "diagnosis_run_id": run["run_id"],
            "repair_type": repair_type,
            "summary": "Prepare a supervised repair preview.",
            "affected_targets": ["config/example.yaml"],
            "proposed_steps": ["Preview the proposed change."],
            "validation_checks": ["contract_tests"],
            "risk_signals": ["contract_violation"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["proposal"]


def diagnosis_model(run_id: str = "maintenance_run_unit") -> DiagnosisResult:
    item = DiagnosisEvidence(
        source_type="event_summary",
        source_id="event_unit",
        summary="Unit evidence.",
        event_ref="event_unit",
        confidence=0.95,
    )
    confidence = DiagnosisConfidence(level="high", score=0.95, reasons=["direct_event_evidence"])
    return DiagnosisResult(
        run_id=run_id,
        status="completed",
        findings=[
            DiagnosisFinding(
                title="unit_finding",
                summary="Structured finding.",
                severity="high",
                evidence_refs=[item.evidence_id],
            )
        ],
        evidence=[item],
        confidence=confidence,
    )


class NullEmitter:
    def __init__(self) -> None:
        self.events: list[str] = []

    def emit(self, event_type: str, *args, **kwargs) -> str:
        self.events.append(event_type)
        return f"event_{event_type}"
