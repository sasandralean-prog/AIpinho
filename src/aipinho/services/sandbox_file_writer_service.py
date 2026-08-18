from __future__ import annotations

import re
import zipfile
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.sandbox_writer import SandboxWriteEvidence, SandboxWriteResult
from aipinho.utils.yaml_loader import load_yaml_file


class SandboxFileWriterService:
    """Minimal governed writer restricted to the configured AIpinho sandbox root."""

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "runtime" / "sandbox_writer.yaml",
            critical=False,
            root=PATHS.config_root / "runtime",
        )
        configured_root = str(self.config.get("root_path") or (PATHS.project_root / "sandboxes"))
        self.root = Path(configured_root).resolve(strict=False)

    def is_sandbox_path(self, path_ref: str | None) -> bool:
        if not path_ref:
            return False
        try:
            return self._is_under(Path(path_ref).resolve(strict=False), self.root)
        except Exception:
            return False

    def write_text_file(self, *, path_ref: str, content: str, overwrite: bool = False) -> SandboxWriteResult:
        run_id = f"sandbox_run_{uuid4().hex}"
        target = Path(path_ref).resolve(strict=False)
        if not self._is_under(target, self.root):
            return self._blocked(run_id, "filesystem_write_file", path_ref, "sandbox_path_required")
        if target.exists() and not overwrite:
            try:
                existing = target.read_text(encoding="utf-8")
            except Exception:
                existing = None
            if existing == content:
                size = target.stat().st_size
                return SandboxWriteResult(
                    status="ready",
                    operation_type="filesystem_write_file",
                    run_id=run_id,
                    path=str(target),
                    size_bytes=size,
                    content_validated=True,
                    policy_decision="allow",
                    approval_decision="autoapproved_safe_sandbox",
                    reason_code="idempotent_existing_content",
                    warnings=["idempotent_existing_content"],
                    evidence=self._evidence(str(target), size, True),
                )
            return self._blocked(run_id, "filesystem_write_file", str(target), "overwrite_requires_explicit_flag")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            size = target.stat().st_size
            readback = target.read_text(encoding="utf-8")
            validated = size > 0 and readback == content
            if not validated:
                return SandboxWriteResult(
                    status="failed",
                    operation_type="filesystem_write_file",
                    run_id=run_id,
                    path=str(target),
                    size_bytes=size,
                    content_validated=False,
                    policy_decision="allow",
                    approval_decision="autoapproved_safe_sandbox",
                    reason_code="file_validation_failed",
                    errors=["file_validation_failed"],
                    evidence=self._evidence(str(target), size, False),
                )
            return SandboxWriteResult(
                status="ready",
                operation_type="filesystem_write_file",
                run_id=run_id,
                path=str(target),
                size_bytes=size,
                content_validated=True,
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                evidence=self._evidence(str(target), size, True),
            )
        except Exception as exc:
            return SandboxWriteResult(
                status="failed",
                operation_type="filesystem_write_file",
                run_id=run_id,
                path=str(target),
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code="sandbox_writer_exception",
                errors=[str(exc)],
            )

    def append_text_file(self, *, path_ref: str, content: str) -> SandboxWriteResult:
        run_id = f"sandbox_run_{uuid4().hex}"
        target = Path(path_ref).resolve(strict=False)
        if not self._is_under(target, self.root):
            return self._blocked(run_id, "filesystem_append_file", path_ref, "sandbox_path_required")
        if not target.exists() or not target.is_file():
            return self._blocked(run_id, "filesystem_append_file", str(target), "file_not_found")
        try:
            before = target.read_text(encoding="utf-8")
            suffix = content if content.endswith("\n") else content + "\n"
            if before.endswith(suffix):
                size = target.stat().st_size
                return SandboxWriteResult(
                    status="ready",
                    operation_type="filesystem_append_file",
                    run_id=run_id,
                    path=str(target),
                    size_bytes=size,
                    content_validated=True,
                    policy_decision="allow",
                    approval_decision="autoapproved_safe_sandbox",
                    reason_code="idempotent_existing_content",
                    warnings=["idempotent_existing_content"],
                    evidence=self._evidence(str(target), size, True),
                )
            target.write_text(before + ("" if before.endswith("\n") or not before else "\n") + suffix, encoding="utf-8")
            readback = target.read_text(encoding="utf-8")
            size = target.stat().st_size
            validated = readback.endswith(suffix)
            return SandboxWriteResult(
                status="ready" if validated else "failed",
                operation_type="filesystem_append_file",
                run_id=run_id,
                path=str(target),
                size_bytes=size,
                content_validated=validated,
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code=None if validated else "file_validation_failed",
                warnings=[] if validated else ["file_validation_failed"],
                evidence=self._evidence(str(target), size, validated),
            )
        except Exception as exc:
            return SandboxWriteResult(
                status="failed",
                operation_type="filesystem_append_file",
                run_id=run_id,
                path=str(target),
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code="sandbox_writer_exception",
                errors=[str(exc)],
            )

    def read_text_file(self, *, path_ref: str, max_chars: int = 12000) -> SandboxWriteResult:
        run_id = f"sandbox_run_{uuid4().hex}"
        target = Path(path_ref).resolve(strict=False)
        if not self._is_under(target, self.root):
            return self._blocked(run_id, "filesystem_read_file", path_ref, "sandbox_path_required")
        if not target.exists() or not target.is_file():
            return self._blocked(run_id, "filesystem_read_file", str(target), "file_not_found")
        try:
            content = target.read_text(encoding="utf-8")
            truncated = len(content) > max_chars
            excerpt = content[:max_chars]
            size = target.stat().st_size
            return SandboxWriteResult(
                status="ready",
                operation_type="filesystem_read_file",
                run_id=run_id,
                path=str(target),
                size_bytes=size,
                content_validated=True,
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code="file_read",
                warnings=["file_content_truncated"] if truncated else [],
                evidence=[
                    *self._evidence(str(target), size, True),
                    SandboxWriteEvidence(
                        evidence_id=f"evidence_{uuid4().hex}",
                        kind="file_excerpt",
                        status="passed",
                        details={"content": excerpt, "truncated": truncated},
                    ),
                ],
            )
        except UnicodeDecodeError:
            return self._blocked(run_id, "filesystem_read_file", str(target), "text_decode_failed")
        except Exception as exc:
            return SandboxWriteResult(
                status="failed",
                operation_type="filesystem_read_file",
                run_id=run_id,
                path=str(target),
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code="sandbox_reader_exception",
                errors=[str(exc)],
            )

    def capability_probe(self, *, content: str | None = None) -> SandboxWriteResult:
        probe_path = self.root / "capability_probe" / f"probe_{uuid4().hex}.txt"
        return self.write_text_file(
            path_ref=str(probe_path),
            content=content or "AIpinho sandbox capability probe.\n",
            overwrite=False,
        )

    def create_text_bundle_archive(self, *, path_ref: str, prompt: str) -> SandboxWriteResult:
        run_id = f"sandbox_run_{uuid4().hex}"
        target_dir = Path(path_ref).resolve(strict=False)
        if not self._is_under(target_dir, self.root):
            return self._blocked(run_id, "sandbox_batch_artifact_request", path_ref, "sandbox_path_required")
        file_count = self._requested_file_count(prompt)
        archive_name = self._requested_archive_name(prompt) or f"{target_dir.name or 'sandbox_bundle'}.zip"
        archive_path = target_dir / archive_name
        evidence: list[SandboxWriteEvidence] = []
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            evidence.append(
                SandboxWriteEvidence(
                    evidence_id=f"evidence_{uuid4().hex}",
                    kind="directory_exists",
                    status="passed",
                    details={"path": str(target_dir)},
                )
            )
            files: list[Path] = []
            for index in range(1, file_count + 1):
                file_path = target_dir / f"arquivo_{index}.txt"
                content = (
                    f"Arquivo {index} criado pelo fluxo governado de sandbox da AIpinho.\n"
                    f"Run: {run_id}\n"
                )
                file_path.write_text(content, encoding="utf-8")
                files.append(file_path)
                evidence.extend(self._evidence(str(file_path), file_path.stat().st_size, True))
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in files:
                    archive.write(file_path, arcname=file_path.name)
            size = archive_path.stat().st_size
            validated = size > 0 and self._zip_contains(archive_path, [file_path.name for file_path in files])
            evidence.append(
                SandboxWriteEvidence(
                    evidence_id=f"evidence_{uuid4().hex}",
                    kind="zip_exists",
                    status="passed" if archive_path.exists() else "failed",
                    details={"path": str(archive_path)},
                )
            )
            evidence.append(
                SandboxWriteEvidence(
                    evidence_id=f"evidence_{uuid4().hex}",
                    kind="zip_size_gt_zero",
                    status="passed" if size > 0 else "failed",
                    details={"size_bytes": size},
                )
            )
            evidence.append(
                SandboxWriteEvidence(
                    evidence_id=f"evidence_{uuid4().hex}",
                    kind="zip_contains_requested_files",
                    status="passed" if validated else "failed",
                    details={"file_count": len(files), "archive": str(archive_path)},
                )
            )
            return SandboxWriteResult(
                status="ready" if validated else "failed",
                operation_type="sandbox_batch_artifact_request",
                run_id=run_id,
                path=str(archive_path),
                size_bytes=size,
                content_validated=validated,
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code=None if validated else "zip_validation_failed",
                warnings=[] if validated else ["zip_validation_failed"],
                evidence=evidence,
            )
        except Exception as exc:
            return SandboxWriteResult(
                status="failed",
                operation_type="sandbox_batch_artifact_request",
                run_id=run_id,
                path=str(archive_path),
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code="sandbox_archive_exception",
                errors=[str(exc)],
                evidence=evidence,
            )

    def create_directory(self, *, path_ref: str) -> SandboxWriteResult:
        run_id = f"sandbox_run_{uuid4().hex}"
        target = Path(path_ref).resolve(strict=False)
        if not self._is_under(target, self.root):
            return self._blocked(run_id, "filesystem_create_directory", path_ref, "sandbox_path_required")
        try:
            target.mkdir(parents=True, exist_ok=True)
            exists = target.exists() and target.is_dir()
            return SandboxWriteResult(
                status="ready" if exists else "failed",
                operation_type="filesystem_create_directory",
                run_id=run_id,
                path=str(target),
                size_bytes=0,
                content_validated=exists,
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code=None if exists else "directory_validation_failed",
                evidence=[
                    SandboxWriteEvidence(
                        evidence_id=f"evidence_{uuid4().hex}",
                        kind="directory_exists",
                        status="passed" if exists else "failed",
                        details={"path": str(target)},
                    )
                ],
            )
        except Exception as exc:
            return SandboxWriteResult(
                status="failed",
                operation_type="filesystem_create_directory",
                run_id=run_id,
                path=str(target),
                policy_decision="allow",
                approval_decision="autoapproved_safe_sandbox",
                reason_code="sandbox_writer_exception",
                errors=[str(exc)],
            )

    def _requested_archive_name(self, prompt: str) -> str | None:
        matches = re.findall(r"(?<![A-Za-z0-9._-])([A-Za-z0-9][A-Za-z0-9._-]{0,119}\.zip)(?![A-Za-z0-9._-])", prompt, flags=re.IGNORECASE)
        return matches[-1] if matches else None

    def _requested_file_count(self, prompt: str) -> int:
        lowered = prompt.casefold()
        digit_match = re.search(r"\b(\d{1,2})\s+(?:arquivos?|files?)\b", lowered)
        if digit_match:
            return max(1, min(20, int(digit_match.group(1))))
        words = {
            "um": 1,
            "uma": 1,
            "dois": 2,
            "duas": 2,
            "tres": 3,
            "três": 3,
            "trÃªs": 3,
            "quatro": 4,
            "cinco": 5,
            "seis": 6,
            "sete": 7,
            "oito": 8,
            "nove": 9,
            "dez": 10,
        }
        for word, count in words.items():
            if re.search(rf"\b{re.escape(word)}\s+(?:arquivos?|files?)\b", lowered):
                return count
        if re.search(r"\btr\S{0,8}s\s+(?:arquivos?|files?)\b", lowered):
            return 3
        return 1

    def _zip_contains(self, archive_path: Path, expected_names: list[str]) -> bool:
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                names = set(archive.namelist())
            return all(name in names for name in expected_names)
        except Exception:
            return False

    def extract_text_content(self, prompt: str) -> str:
        patterns = [
            r"(?:conte[úu]do|texto|contendo|com\s+o\s+texto|with\s+content)\s*[:=]?\s*[\"']([^\"']+)[\"']",
            r"(?:conte[úu]do|texto|contendo|com\s+o\s+texto|with\s+content)\s*[:=]?\s*`([^`]+)`",
            r"(?:conte[úu]do|texto|contendo|com\s+o\s+texto|with\s+content)\s*[:=]?\s*(.+)$",
            r":\s*([^:\r\n][\s\S]+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip().strip('"').strip("'")
                if content:
                    return content.rstrip("\n") + "\n"
        return "Arquivo criado pelo fluxo governado de sandbox da AIpinho.\n"

    def _blocked(self, run_id: str, operation_type: str, path_ref: str, reason_code: str) -> SandboxWriteResult:
        return SandboxWriteResult(
            status="blocked",
            operation_type=operation_type,
            run_id=run_id,
            path=path_ref,
            policy_decision="deny",
            approval_decision="not_applicable",
            reason_code=reason_code,
            warnings=[reason_code],
        )

    def _evidence(self, path: str, size: int, validated: bool) -> list[SandboxWriteEvidence]:
        return [
            SandboxWriteEvidence(
                evidence_id=f"evidence_{uuid4().hex}",
                kind="file_exists",
                status="passed",
                details={"path": path},
            ),
            SandboxWriteEvidence(
                evidence_id=f"evidence_{uuid4().hex}",
                kind="file_size_gt_zero",
                status="passed" if size > 0 else "failed",
                details={"size_bytes": size},
            ),
            SandboxWriteEvidence(
                evidence_id=f"evidence_{uuid4().hex}",
                kind="content_validated",
                status="passed" if validated else "failed",
                details={"validated": validated},
            ),
        ]

    def _is_under(self, path: Path, root: Path) -> bool:
        return path == root or root in path.parents

    def status(self) -> dict[str, object]:
        return {"status": "ok", "root_path": str(self.root), "enabled": bool(self.config.get("enabled", True))}
