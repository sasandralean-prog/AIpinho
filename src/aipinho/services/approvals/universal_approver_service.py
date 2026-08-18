from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.universal_approver import (
    ApprovalOrigin,
    ApprovalSignature,
    UniversalApprovalDecisionResult,
    UniversalApprovalTextRequest,
    UniversalApprover,
    UniversalApproverUpsertRequest,
)
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_service import ApprovalService, snapshot_hash
from aipinho.services.approvals.approval_task_continuation_service import ApprovalTaskContinuationService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import load_yaml_file


class UniversalApproverService:
    APPROVE_RE = re.compile(r"\b(approve|approved|aprovar|aprovado|autorizo|autorizado|permito|permitido)\b", re.IGNORECASE)
    REJECT_RE = re.compile(r"\b(deny|denied|reject|rejected|negar|negado|rejeitar|rejeitado|bloquear|bloqueado)\b", re.IGNORECASE)

    def __init__(
        self,
        *,
        approval_service: ApprovalService | None = None,
        config_path: Path | None = None,
        store_path: Path | None = None,
    ) -> None:
        self.approvals = approval_service or ApprovalService()
        self.config_path = config_path or PATHS.config_root / "governance" / "approval_capability_matrix.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=PATHS.config_root / "governance")
        self.store_path = store_path or PATHS.project_root / "data" / "runtime" / "universal_approvers" / "approvers.json"

    def list_approvers(self) -> list[UniversalApprover]:
        records = self._default_approvers()
        records.update(self._stored_approvers())
        return sorted(records.values(), key=lambda item: (item.trust_level, item.approver_id))

    def get_approver(self, approver_id: str) -> UniversalApprover | None:
        normalized = self._normalize_id(approver_id)
        for approver in self.list_approvers():
            if approver.approver_id == normalized:
                return approver
        return None

    def upsert_approver(self, request: UniversalApproverUpsertRequest) -> UniversalApprover:
        approver = UniversalApprover(
            approver_id=self._normalize_id(request.approver_id),
            display_name=request.display_name,
            approver_type=request.approver_type,
            trust_level=request.trust_level,
            capabilities=self._normalize_capabilities(request.capabilities),
            status=request.status,
            metadata=request.metadata,
        )
        records = self._stored_approvers()
        existing = records.get(approver.approver_id)
        if existing:
            approver.created_at = existing.created_at
        approver.updated_at = utc_now()
        records[approver.approver_id] = approver
        self._save_stored_approvers(records)
        return approver

    def decide_from_text(self, approval_id: str, request: UniversalApprovalTextRequest) -> UniversalApprovalDecisionResult:
        approver = self.get_approver(request.approver_id)
        if approver is None:
            return self._blocked(approval_id, request.approver_id, "unknown_approver", "Approver desconhecido.")
        if approver.status != "active":
            return self._blocked(approval_id, approver.approver_id, f"approver_{approver.status}", "Approver nao esta ativo.")
        approval = self.approvals.get_approval(approval_id)
        if approval is None:
            return self._blocked(approval_id, approver.approver_id, "approval_not_found", "ApprovalRequest nao encontrado.")
        if approval.status != "pending":
            reason_code = "approval_expired" if approval.status == "expired" else f"approval_not_pending:{approval.status}"
            return self._blocked(
                approval_id,
                approver.approver_id,
                reason_code,
                f"ApprovalRequest nao esta pendente: {approval.status}.",
            )
        decision = self._decision_from_text(request.text)
        if decision is None:
            self.approvals.append_event(
                approval.approval_id,
                "universal_approval_decision_rejected",
                "Texto do approver nao continha decisao clara.",
                {"approver_id": approver.approver_id, "authority": "AIpinho"},
            )
            return self._blocked(approval_id, approver.approver_id, "approval_text_ambiguous", "Texto nao indicou approve/deny de forma inequivoca.")
        ok, reason_code, category = self._can_approve(approver, approval.actions_requested)
        if not ok:
            event_type = "universal_approval_trust_denied" if reason_code == "trust_level_denied" else "universal_approval_capability_denied"
            self.approvals.append_event(
                approval.approval_id,
                event_type,
                "Universal Approver nao tem autoridade suficiente para esta categoria.",
                {"approver_id": approver.approver_id, "category": category, "actions": approval.actions_requested, "authority": "AIpinho"},
            )
            return self._blocked(approval_id, approver.approver_id, reason_code, f"Approver sem autoridade para {category}.")
        signature = self._signature(approval, approver, decision, request)
        origin = ApprovalOrigin(
            origin_type=approver.approver_type,
            origin_id=approver.approver_id,
            requested_by=request.requested_by,
            approved_by=approver.approver_id,
            approval_authority="AIpinho",
            signature=signature.signature,
            timestamp=signature.timestamp,
        )
        self.approvals.append_event(
            approval.approval_id,
            "universal_approval_decision_received",
            "Decisao textual recebida de Universal Approver.",
            {"approver_id": approver.approver_id, "decision": decision, "authority": "AIpinho"},
        )
        try:
            if decision == "approved":
                approval_decision, updated = self.approvals.approve(
                    approval.approval_id,
                    actor=Actor(type="system", id=f"universal_approver:{approver.approver_id}"),
                    reason=request.reason or request.text[:500],
                    scope="universal_approver_text",
                    approval_origin=origin,
                    approval_signature=signature,
                )
            else:
                approval_decision, updated = self.approvals.reject(
                    approval.approval_id,
                    actor=Actor(type="system", id=f"universal_approver:{approver.approver_id}"),
                    reason=request.reason or request.text[:500],
                    scope="universal_approver_text",
                    approval_origin=origin,
                    approval_signature=signature,
                )
        except ValueError as exc:
            return self._blocked(approval_id, approver.approver_id, str(exc), "ApprovalService recusou a decisao.")
        self.approvals.append_event(
            updated.approval_id,
            "universal_approval_signature_created",
            "Assinatura de approval registrada.",
            {"signature_id": signature.signature_id, "approver_id": approver.approver_id, "authority": "AIpinho"},
        )
        self.approvals.append_event(
            updated.approval_id,
            "universal_approval_decision_accepted",
            "Decisao universal aceita; execucao continua apenas pelo runtime governado.",
            {"approver_id": approver.approver_id, "decision": approval_decision.decision, "authority": "AIpinho"},
        )
        resume = ApprovalTaskContinuationService(approvals=self.approvals).after_decision(updated)
        return UniversalApprovalDecisionResult(
            status="ok",
            approval_id=updated.approval_id,
            decision=decision,
            approver_id=approver.approver_id,
            human_summary="Approval registrado pela AIpinho com assinatura de Universal Approver. Nenhum bypass foi executado.",
            approval_origin=origin,
            approval_signature=signature,
            approval=updated.model_dump(),
            resume=resume,
        )

    def timeline(self, *, limit: int = 100) -> dict[str, Any]:
        approvals = self.approvals.list_approvals(status=None, limit=limit)
        items = []
        for approval in approvals:
            events = self.approvals.list_events(approval.approval_id)
            signature = approval.approval_signature.model_dump() if approval.approval_signature else None
            origin = approval.approval_origin.model_dump() if approval.approval_origin else None
            items.append({
                "approval_id": approval.approval_id,
                "status": approval.status,
                "operation_type": approval.operation_type,
                "actions_requested": approval.actions_requested,
                "approver_id": approval.approval_origin.approved_by if approval.approval_origin else None,
                "authority": approval.approval_authority,
                "signature": signature,
                "origin": origin,
                "updated_at": approval.updated_at,
                "events": [event.model_dump() for event in events[-10:]],
            })
        return {"status": "ok", "authority": "AIpinho", "items": items[: max(1, min(limit, 1000))]}

    def mobile_view_model(self) -> dict[str, Any]:
        approvers = [item.model_dump() for item in self.list_approvers()]
        timeline = self.timeline(limit=50)
        return {
            "status": "ok",
            "authority": "AIpinho",
            "cards": [
                {
                    "card_id": "universal_approvers",
                    "title": "Universal Approvers",
                    "card_type": "universal_approvers",
                    "status": "healthy",
                    "metadata": {"approvers": approvers, "count": len(approvers)},
                },
                {
                    "card_id": "approval_timeline",
                    "title": "Approval Timeline",
                    "card_type": "approval_timeline",
                    "status": "healthy",
                    "metadata": {"timeline": timeline["items"], "count": len(timeline["items"])},
                },
            ],
        }

    def _can_approve(self, approver: UniversalApprover, actions: list[str]) -> tuple[bool, str | None, str]:
        categories = self._categories_for_actions(actions)
        if not categories:
            categories = ["contracts"]
        for category in categories:
            if not self._trust_allows(approver.trust_level, str(self.config.get("minimum_trust_by_category", {}).get(category, "L1"))):
                return False, "trust_level_denied", category
            if "approve" not in set(approver.capabilities.get(category, [])):
                return False, "capability_denied", category
        return True, None, ",".join(categories)

    def _categories_for_actions(self, actions: list[str]) -> list[str]:
        mapping = self.config.get("action_category_map", {}) if isinstance(self.config.get("action_category_map"), dict) else {}
        categories = []
        for action in actions or []:
            categories.append(str(mapping.get(str(action), "contracts")))
        return list(dict.fromkeys(categories))

    def _trust_allows(self, actual: str, minimum: str) -> bool:
        order = self.config.get("trust_order", {}) if isinstance(self.config.get("trust_order"), dict) else {}
        return int(order.get(actual, -1)) >= int(order.get(minimum, 999))

    def _signature(self, approval, approver: UniversalApprover, decision: str, request: UniversalApprovalTextRequest) -> ApprovalSignature:
        timestamp = utc_now()
        material = {
            "approval_id": approval.approval_id,
            "approver_id": approver.approver_id,
            "decision": decision,
            "timestamp": timestamp,
            "policy_snapshot_hash": snapshot_hash(approval.policy_snapshot),
            "preview_hash": approval.preview_hash,
            "text_hash": hashlib.sha256(request.text.encode("utf-8")).hexdigest(),
            "authority": "AIpinho",
        }
        signature = hashlib.sha256(json.dumps(material, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
        return ApprovalSignature(
            approver_id=approver.approver_id,
            session_id=request.session_id,
            collaboration_session=request.collaboration_session,
            timestamp=timestamp,
            reason=request.reason or request.text[:500],
            speaker_truth_reference="approval_decision_recorded_without_execution",
            signature=signature,
            metadata={"material": material, "authority": "AIpinho", **request.metadata},
        )

    def _decision_from_text(self, text: str) -> str | None:
        approved = bool(self.APPROVE_RE.search(text or ""))
        rejected = bool(self.REJECT_RE.search(text or ""))
        if approved == rejected:
            return None
        return "approved" if approved else "rejected"

    def _default_approvers(self) -> dict[str, UniversalApprover]:
        defaults = self.config.get("default_approvers", {}) if isinstance(self.config.get("default_approvers"), dict) else {}
        records = {}
        for approver_id, payload in defaults.items():
            if not isinstance(payload, dict):
                continue
            records[self._normalize_id(approver_id)] = UniversalApprover(
                approver_id=self._normalize_id(approver_id),
                display_name=str(payload.get("display_name") or approver_id),
                approver_type=payload.get("approver_type") or "external_adapter",
                trust_level=payload.get("trust_level") or "L1",
                capabilities=self._normalize_capabilities(payload.get("capabilities") or {}),
                status=payload.get("status") or "active",
                metadata={k: v for k, v in payload.items() if k not in {"display_name", "approver_type", "trust_level", "capabilities", "status"}},
            )
        return records

    def _stored_approvers(self) -> dict[str, UniversalApprover]:
        if not self.store_path.exists():
            return {}
        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        return {
            self._normalize_id(item["approver_id"]): UniversalApprover.model_validate(item)
            for item in data.get("approvers", [])
            if isinstance(item, dict) and item.get("approver_id")
        }

    def _save_stored_approvers(self, records: dict[str, UniversalApprover]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"approvers": [item.model_dump() for item in sorted(records.values(), key=lambda row: row.approver_id)]}
        self.store_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _normalize_id(value: str) -> str:
        return re.sub(r"[^a-z0-9_.:-]+", "_", str(value).strip().lower()).strip("_")

    @staticmethod
    def _normalize_capabilities(value: dict[str, Any]) -> dict[str, list[str]]:
        normalized: dict[str, list[str]] = {}
        for category, capabilities in (value or {}).items():
            if isinstance(capabilities, str):
                items = [capabilities]
            else:
                items = [str(item) for item in capabilities or []]
            normalized[str(category)] = list(dict.fromkeys(item for item in items if item in {"approve", "deny", "review", "plan"}))
        return normalized

    @staticmethod
    def _blocked(approval_id: str, approver_id: str, reason_code: str, summary: str) -> UniversalApprovalDecisionResult:
        return UniversalApprovalDecisionResult(
            status="blocked",
            approval_id=approval_id,
            approver_id=approver_id,
            reason_code=reason_code,
            human_summary=summary,
        )
