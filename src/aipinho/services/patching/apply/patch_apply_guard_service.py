from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.patching.apply.patch_apply_guard import PatchApplyGuardResult
from aipinho.schemas.patching.apply.patch_apply_request import PatchApplyRequest
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.quality.patch_quality_gate_result import PatchQualityGateResult
from aipinho.core.paths import PATHS
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.patching.apply.patch_apply_hashing import sha256_file, sha256_text
from aipinho.utils.yaml_loader import load_yaml_file
from aipinho.utils.safe_paths import resolve_within_root


class PatchApplyGuardService:
    SECRET_SUFFIXES = {".env", ".pem", ".key", ".pfx", ".sqlite", ".db", ".bin", ".exe", ".dll"}

    def __init__(self) -> None:
        policy_path = PATHS.config_root / "patching" / "apply" / "patch_apply_policy.yaml"
        self.policy = load_yaml_file(policy_path, critical=True, root=policy_path.parent)

    def validate(self, plan: PatchPlan | None, quality: PatchQualityGateResult | None, request: PatchApplyRequest, approval_service: ApprovalService | None = None) -> PatchApplyGuardResult:
        blocking: list[str] = []
        warnings: list[str] = []
        approval_service = approval_service or ApprovalService()
        approval: ApprovalRequest | None = None
        diff_hash = sha256_text(plan.diff_proposal.diff.diff_text) if plan and plan.diff_proposal else None
        target_files = [file.relative_path or file.path for file in plan.affected_files] if plan else []
        if plan is None:
            blocking.append("patch_plan_not_found")
        elif plan.diff_proposal is None or not plan.diff_proposal.diff.diff_text:
            blocking.append("patch_diff_not_found")
        if quality is None:
            blocking.append("patch_quality_missing")
        elif quality.status != "passed":
            blocking.append(f"patch_quality_not_passed:{quality.status}")
        if not request.operator_confirmed:
            blocking.append("operator_confirmation_required")
        if not request.approval_id:
            blocking.append("approval_required")
        else:
            approval = approval_service.get_approval(request.approval_id)
            if approval is None:
                blocking.append("approval_not_found")
            elif approval.status != "approved":
                blocking.append(f"approval_not_approved:{approval.status}")
            else:
                if approval.approval_scope != "patch_apply":
                    blocking.append("approval_scope_mismatch")
                if approval.preview_id != (plan.plan_id if plan else None):
                    blocking.append("approval_plan_id_mismatch")
                if self._is_expired(approval.expires_at):
                    blocking.append("approval_expired")
                versions = approval.policy_snapshot.config_versions
                if diff_hash and versions.get("diff_hash") != diff_hash:
                    blocking.append("diff_hash_mismatch")
                if sorted(versions.get("target_files", []) or []) != sorted(target_files):
                    blocking.append("target_files_mismatch")
        if plan is not None:
            workspace_root = Path(plan.workspace)
            for file in plan.affected_files:
                rel = file.relative_path or file.path
                path_text = file.normalized_path or ""
                if not path_text:
                    blocking.append(f"target_missing_normalized_path:{rel}")
                    continue
                path = Path(path_text)
                try:
                    resolve_within_root(path, workspace_root)
                except Exception:
                    blocking.append(f"target_outside_workspace:{rel}")
                if ".." in rel.replace("\\", "/").split("/"):
                    blocking.append(f"path_traversal:{rel}")
                if path.is_symlink():
                    blocking.append(f"target_symlink:{rel}")
                create_file_allowed = self._create_file_allowed() and self._is_create_file_plan(plan, rel)
                if (not path.exists() or not path.is_file()) and not create_file_allowed:
                    blocking.append(f"target_file_missing:{rel}")
                if path.suffix.lower() in self.SECRET_SUFFIXES or path.name.lower() in {".env"}:
                    blocking.append(f"target_secret_or_binary:{rel}")
                if file.original_hash and path.exists() and sha256_file(path) != file.original_hash:
                    blocking.append(f"stale_snapshot:{rel}")
        return PatchApplyGuardResult(
            status="allowed" if not blocking else "blocked",
            allowed=not blocking,
            blocking_reasons=list(dict.fromkeys(blocking)),
            warnings=warnings,
            plan_id=plan.plan_id if plan else None,
            quality_id=quality.quality_id if quality else None,
            approval_id=request.approval_id,
            diff_hash=diff_hash,
            target_files=target_files,
        )

    def _is_expired(self, expires_at: str) -> bool:
        try:
            return datetime.fromisoformat(expires_at) < datetime.now(timezone.utc)
        except Exception:
            return True

    def _create_file_allowed(self) -> bool:
        allowed = self.policy.get("allowed_mutations", {}) if isinstance(self.policy.get("allowed_mutations"), dict) else {}
        blocked = self.policy.get("blocked", {}) if isinstance(self.policy.get("blocked"), dict) else {}
        return bool(allowed.get("create_file", False)) and not bool(blocked.get("new_file", True))

    def _is_create_file_plan(self, plan: PatchPlan, rel: str) -> bool:
        normalized = rel.replace("\\", "/")
        for affected in plan.affected_files:
            affected_rel = (affected.relative_path or affected.path).replace("\\", "/")
            if affected_rel == normalized and affected.original_hash:
                return False
        hunks = [hunk for hunk in plan.hunks if hunk.file_path.replace("\\", "/") == normalized]
        return bool(hunks) and all(hunk.original == "" for hunk in hunks)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_guard", "create_file_allowed": self._create_file_allowed(), "shell_enabled": False, "git_enabled": False}
