
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aipinho.core.paths import PATHS
from aipinho.schemas.legacy_rag.contracts import (
    LegacyClassifiedChunk,
    LegacyConflict,
    LegacyImportStageResult,
    LegacyReviewDecision,
    LegacyRAGStatus,
    LegacySanitizedChunk,
    LegacySourceFile,
)
from aipinho.utils.yaml_loader import load_yaml_file


NAMESPACE_ID = "legacy_pinhoabacaxi_curated"
BASE = PATHS.project_root / "data" / "runtime" / "legacy_rag_import"
NAMESPACE_DIR = PATHS.project_root / "data" / "runtime" / "rag" / "namespaces" / NAMESPACE_ID
STAGE_DIRS = (
    "inventory",
    "quarantine",
    "sanitized",
    "classified",
    "review_queue",
    "approved",
    "rejected",
    "conflicts",
    "regression_candidates",
    "lessons",
    "audit",
)


def _json_default(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n" for row in rows), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def load_policy(name: str) -> dict[str, object]:
    return load_yaml_file(PATHS.config_root / "rag" / name, critical=False)


def ensure_dirs() -> None:
    for folder in STAGE_DIRS:
        (BASE / folder).mkdir(parents=True, exist_ok=True)
    NAMESPACE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class LegacyRAGPaths:
    inventory: Path = BASE / "inventory" / "legacy_inventory.jsonl"
    scan_result: Path = BASE / "inventory" / "legacy_scan_result.json"
    quarantine: Path = BASE / "quarantine" / "legacy_quarantine_manifest.jsonl"
    sanitized: Path = BASE / "sanitized" / "legacy_sanitized_chunks.jsonl"
    classified: Path = BASE / "classified" / "legacy_classified_chunks.jsonl"
    conflicts: Path = BASE / "conflicts" / "legacy_conflicts.jsonl"
    review: Path = BASE / "review_queue" / "legacy_review_decisions.jsonl"
    approved: Path = BASE / "approved" / "legacy_approved_chunks.jsonl"
    rejected: Path = BASE / "rejected" / "legacy_rejected_chunks.jsonl"
    regressions: Path = BASE / "regression_candidates" / "legacy_regression_candidates.jsonl"
    lessons: Path = BASE / "lessons" / "legacy_lesson_candidates.jsonl"
    audit: Path = BASE / "audit" / "legacy_rag_import_audit.jsonl"
    namespace_manifest: Path = NAMESPACE_DIR / "manifest.json"
    namespace_chunks: Path = NAMESPACE_DIR / "chunks.jsonl"


PATHS43 = LegacyRAGPaths()


def audit(event_type: str, payload: dict[str, object]) -> None:
    ensure_dirs()
    rows = read_jsonl(PATHS43.audit)
    rows.append({"event_type": event_type, "timestamp": time.time(), "payload": payload})
    write_jsonl(PATHS43.audit, rows)


class LegacyFileScanner:
    def __init__(self) -> None:
        policy = load_policy("legacy_rag_import_policy.yaml")
        self.source_roots = [Path(str(path)) for path in policy.get("source_roots", [])]
        self.allowed_extensions = set(policy.get("allowed_extensions", []))
        self.ignored_dirs = set(policy.get("ignored_dirs", []))
        self.max_file_bytes = int(policy.get("max_file_bytes", 1_500_000))

    def scan_sources(self) -> LegacyImportStageResult:
        ensure_dirs()
        included: list[dict[str, object]] = []
        quarantined: list[dict[str, object]] = []
        warnings: list[str] = []
        for source_root in self.source_roots:
            if not source_root.exists():
                warnings.append(f"missing_source_root:{source_root}")
                continue
            for dirpath, dirnames, filenames in os.walk(source_root, followlinks=False):
                dirnames[:] = [name for name in dirnames if name not in self.ignored_dirs and not name.startswith(".git")]
                base = Path(dirpath)
                for filename in filenames:
                    path = base / filename
                    rel = str(path.relative_to(source_root))
                    ext = path.suffix.lower()
                    stat = path.stat()
                    source_kind = self._source_kind(source_root, ext)
                    source_id = stable_id("legacy_source", str(path), stat.st_size, stat.st_mtime_ns)
                    if ext not in self.allowed_extensions:
                        quarantined.append(LegacySourceFile(source_id=source_id, path=str(path), relative_path=rel, source_root=str(source_root), source_kind=source_kind, extension=ext, size_bytes=stat.st_size, included=False, ignored_reason="unsupported_extension").model_dump())
                        continue
                    record = LegacySourceFile(source_id=source_id, path=str(path), relative_path=rel, source_root=str(source_root), source_kind=source_kind, extension=ext, size_bytes=stat.st_size, sha256=sha256_file(path), included=True).model_dump()
                    if stat.st_size > self.max_file_bytes:
                        record["ignored_reason"] = "large_file_sanitized_excerpt_only"
                    included.append(record)
        write_jsonl(PATHS43.inventory, included)
        write_jsonl(PATHS43.quarantine, quarantined)
        result = LegacyImportStageResult(status="ok", stage="scan", counts={"included": len(included), "quarantined": len(quarantined)}, warnings=warnings, artifacts={"inventory": str(PATHS43.inventory), "quarantine": str(PATHS43.quarantine)})
        write_json(PATHS43.scan_result, result.model_dump())
        audit("legacy_rag_inventory_completed", result.model_dump())
        return result

    def _source_kind(self, source_root: Path, ext: str) -> str:
        lowered = str(source_root).lower()
        if "reports" in lowered:
            return "legacy_report"
        if "docs" in lowered:
            return "legacy_doc"
        if "knowledge" in lowered:
            return "legacy_knowledge_base"
        if "memory" in lowered:
            return "legacy_memory"
        if ext == ".log":
            return "legacy_log"
        return "legacy_file"


class LegacySanitizationService:
    SECRET_PATTERNS = [
        (re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{12,})"), r"\1=[REDACTED_SECRET]"),
        (re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{16,}"), "Bearer [REDACTED_SECRET]"),
        (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----.*?-----END [A-Z ]+PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
        (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "[REDACTED_API_KEY]"),
    ]

    def __init__(self) -> None:
        policy = load_policy("legacy_rag_sanitization_policy.yaml")
        self.max_chunk_chars = int(policy.get("max_chunk_chars", 2200))
        self.overlap_chars = int(policy.get("overlap_chars", 160))
        self.max_read_bytes = int(policy.get("max_read_bytes", 1_500_000))

    def sanitize_inventory(self) -> LegacyImportStageResult:
        ensure_dirs()
        inventory = [LegacySourceFile(**row) for row in read_jsonl(PATHS43.inventory)]
        chunks: list[dict[str, object]] = []
        warnings: list[str] = []
        for source in inventory:
            path = Path(source.path)
            try:
                raw = path.read_bytes()[: self.max_read_bytes]
                text = raw.decode("utf-8", errors="replace")
            except OSError as exc:
                warnings.append(f"read_failed:{source.path}:{exc}")
                continue
            sanitized, redactions = self.sanitize_text(text)
            sanitized = self._strip_raw_noise(sanitized)
            for index, piece in enumerate(self.chunk_text(sanitized)):
                summary = self.summarize(piece)
                chunk = LegacySanitizedChunk(
                    chunk_id=stable_id("legacy_chunk", source.source_id, index, summary),
                    source_id=source.source_id,
                    source_path=source.path,
                    source_hash=source.sha256 or "",
                    chunk_index=index,
                    text=piece,
                    summary=summary,
                    source_kind=source.source_kind,
                    citations=[f"{source.relative_path}#chunk-{index}"],
                    redactions=redactions,
                    raw_reference=stable_id("legacy_raw_ref", source.source_id, index),
                    metadata={"relative_path": source.relative_path, "legacy_only": True, "truncated_source": source.ignored_reason == "large_file_sanitized_excerpt_only"},
                )
                chunks.append(chunk.model_dump())
        write_jsonl(PATHS43.sanitized, chunks)
        result = LegacyImportStageResult(status="ok", stage="sanitize", counts={"chunks": len(chunks), "sources": len(inventory)}, warnings=warnings, artifacts={"sanitized": str(PATHS43.sanitized)})
        audit("legacy_rag_sanitization_completed", result.model_dump())
        return result

    def sanitize_text(self, text: str) -> tuple[str, list[str]]:
        redactions: list[str] = []
        sanitized = text.replace("\x00", "")
        for pattern, repl in self.SECRET_PATTERNS:
            if pattern.search(sanitized):
                redactions.append(pattern.pattern[:60])
            sanitized = pattern.sub(repl, sanitized)
        sanitized = re.sub(r"C:\\Dev\\AI\\coding-brain-supervisor", "[LEGACY_SOURCE_ROOT]", sanitized, flags=re.I)
        sanitized = re.sub(r"C:\\PinhoabacaxiAI", "[PROTECTED_LEGACY_PROJECT]", sanitized, flags=re.I)
        return sanitized, redactions

    def _strip_raw_noise(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            if len(line) > 1200:
                line = line[:1200] + " [TRUNCATED_LONG_LINE]"
            lines.append(line.rstrip())
        return "\n".join(lines).strip()

    def chunk_text(self, text: str) -> list[str]:
        if not text:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.max_chunk_chars)
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(0, end - self.overlap_chars)
        return [chunk for chunk in chunks if chunk]

    def summarize(self, text: str) -> str:
        for line in text.splitlines():
            clean = line.strip(" #\t-")
            if len(clean) >= 20:
                return clean[:220]
        return text.strip().replace("\n", " ")[:220]


class LegacyClassificationService:
    def classify(self) -> LegacyImportStageResult:
        ensure_dirs()
        rows = [LegacySanitizedChunk(**row) for row in read_jsonl(PATHS43.sanitized)]
        classified: list[dict[str, object]] = []
        for row in rows:
            text = f"{row.summary}\n{row.text}".lower()
            categories = self.categories_for(text)
            deprecated = self.deprecated_signals(text)
            pinhoforge = "pinhoforge" in text or "pinho forge" in text
            classified.append(LegacyClassifiedChunk(**row.model_dump(), categories=categories, pinhoforge_specific=pinhoforge, deprecated_signals=deprecated).model_dump())
        write_jsonl(PATHS43.classified, classified)
        result = LegacyImportStageResult(status="ok", stage="classify", counts={"classified": len(classified)}, artifacts={"classified": str(PATHS43.classified)})
        audit("legacy_rag_classification_completed", result.model_dump())
        return result

    def categories_for(self, text: str) -> list[str]:
        text = text.lower()
        categories = set()
        mapping = {
            "architecture_lesson": ("architecture", "modular", "monolith", "runtime", "facade"),
            "policy_lesson": ("policy", "approval", "capability", "quality gate", "qualitygate", "forbidden", "security"),
            "ux_lesson": ("mobile", "launcher", "workbench", "ux", "chat", "debugger"),
            "rag_memory_lesson": ("rag", "memory", "vector", "embedding", "curated"),
            "regression_signal": ("failed", "bug", "regression", "pendÃªncia", "failure"),
            "legacy_route_reference": ("/v1", "/chat", "/codex", "deprecated", "legacy"),
            "legacy_pinhoforge_reference": ("pinhoforge", "pinho forge"),
        }
        for category, needles in mapping.items():
            if any(needle in text for needle in needles):
                categories.add(category)
        if not categories:
            categories.add("legacy_context")
        return sorted(categories)

    def deprecated_signals(self, text: str) -> list[str]:
        signals = []
        for needle in ("/v1", "/chat", "/codex", "deprecated", "legacy_server_runtime", "8088", "8089"):
            if needle in text:
                signals.append(needle)
        return signals


class LegacyConflictDetectionService:
    def detect(self) -> LegacyImportStageResult:
        ensure_dirs()
        rows = [LegacyClassifiedChunk(**row) for row in read_jsonl(PATHS43.classified)]
        conflicts: list[dict[str, object]] = []
        for row in rows:
            evidence = []
            if row.deprecated_signals:
                evidence.extend(row.deprecated_signals)
            if row.pinhoforge_specific:
                evidence.append("legacy_project_specific_reference")
            if "current truth" in row.text.lower() or "source of truth" in row.text.lower():
                evidence.append("legacy_truth_language")
            if evidence:
                conflicts.append(LegacyConflict(conflict_id=stable_id("legacy_conflict", row.chunk_id, ",".join(evidence)), chunk_id=row.chunk_id, conflict_type="legacy_current_conflict", severity="medium", evidence=evidence).model_dump())
        write_jsonl(PATHS43.conflicts, conflicts)
        result = LegacyImportStageResult(status="ok", stage="conflicts", counts={"conflicts": len(conflicts)}, artifacts={"conflicts": str(PATHS43.conflicts)})
        audit("legacy_rag_conflict_detected", result.model_dump())
        return result


class LegacyReviewService:
    def summarize_review(self) -> LegacyImportStageResult:
        ensure_dirs()
        rows = [LegacyClassifiedChunk(**row) for row in read_jsonl(PATHS43.classified)]
        conflict_ids = {row["chunk_id"] for row in read_jsonl(PATHS43.conflicts)}
        decisions: list[dict[str, object]] = []
        approved: list[dict[str, object]] = []
        rejected: list[dict[str, object]] = []
        regressions: list[dict[str, object]] = []
        lessons: list[dict[str, object]] = []
        by_id = {row.chunk_id: row for row in rows}
        for row in rows:
            status = "approved"
            reason = "sanitized_legacy_lesson_with_scope"
            if row.chunk_id in conflict_ids or row.pinhoforge_specific:
                status = "needs_human_review"
                reason = "legacy_specific_or_conflicting_reference"
            if len(row.text.strip()) < 80:
                status = "rejected"
                reason = "low_information_chunk"
            decision = LegacyReviewDecision(chunk_id=row.chunk_id, status=status, reason=reason, allowed_uses=["historical_diagnostic", "regression_seed", "lesson_candidate"] if status == "approved" else [], blocked_uses=["current_truth", "automatic_curated_memory"]).model_dump()
            decisions.append(decision)
            if status == "approved":
                approved.append(row.model_dump())
                if "regression_signal" in row.categories:
                    regressions.append({"candidate_id": stable_id("legacy_regression", row.chunk_id), "chunk_id": row.chunk_id, "summary": row.summary, "evidence": row.citations, "status": "candidate"})
                if any(category.endswith("_lesson") for category in row.categories):
                    lessons.append({"candidate_id": stable_id("legacy_lesson", row.chunk_id), "chunk_id": row.chunk_id, "summary": row.summary, "evidence": row.citations, "status": "candidate"})
            elif status == "rejected":
                rejected.append(row.model_dump())
        write_jsonl(PATHS43.review, decisions)
        write_jsonl(PATHS43.approved, approved)
        write_jsonl(PATHS43.rejected, rejected)
        write_jsonl(PATHS43.regressions, regressions)
        write_jsonl(PATHS43.lessons, lessons)
        result = LegacyImportStageResult(status="ok", stage="review", counts={"approved": len(approved), "rejected": len(rejected), "needs_human_review": sum(1 for row in decisions if row["status"] == "needs_human_review"), "regression_candidates": len(regressions), "lesson_candidates": len(lessons)}, artifacts={"review": str(PATHS43.review), "approved": str(PATHS43.approved), "rejected": str(PATHS43.rejected)})
        audit("legacy_rag_review_decision_recorded", result.model_dump())
        return result

    def import_preview(self) -> LegacyImportStageResult:
        approved = read_jsonl(PATHS43.approved)
        manifest = {"namespace_id": NAMESPACE_ID, "committed": False, "approval_required": True, "approved_preview_chunks": len(approved), "allowed_use": "historical_diagnostic_only", "current_truth_allowed": False}
        write_json(PATHS43.namespace_manifest, manifest)
        result = LegacyImportStageResult(status="needs_approval", stage="import-preview", counts={"approved_preview_chunks": len(approved)}, warnings=["commit_requires_explicit_approval_manifest"], artifacts={"namespace_manifest": str(PATHS43.namespace_manifest)})
        audit("legacy_rag_namespace_preview_created", result.model_dump())
        return result

    def commit(self, approval_manifest: Path) -> LegacyImportStageResult:
        if not approval_manifest.exists():
            result = LegacyImportStageResult(status="blocked", stage="commit", warnings=["approval_manifest_missing"], artifacts={"expected_approval_manifest": str(approval_manifest)})
            audit("legacy_rag_import_commit_blocked", result.model_dump())
            return result
        approval = json.loads(approval_manifest.read_text(encoding="utf-8"))
        if approval.get("approved") is not True or approval.get("namespace_id") != NAMESPACE_ID:
            result = LegacyImportStageResult(status="blocked", stage="commit", warnings=["approval_manifest_invalid"], artifacts={"approval_manifest": str(approval_manifest)})
            audit("legacy_rag_import_commit_blocked", result.model_dump())
            return result
        approved = read_jsonl(PATHS43.approved)
        write_jsonl(PATHS43.namespace_chunks, approved)
        manifest = {"namespace_id": NAMESPACE_ID, "committed": True, "approval_manifest": str(approval_manifest), "chunks": len(approved), "current_truth_allowed": False}
        write_json(PATHS43.namespace_manifest, manifest)
        result = LegacyImportStageResult(status="ok", stage="commit", counts={"chunks": len(approved)}, artifacts={"namespace_chunks": str(PATHS43.namespace_chunks), "namespace_manifest": str(PATHS43.namespace_manifest)})
        audit("legacy_rag_import_committed", result.model_dump())
        return result


class LegacyRAGPipelineService:
    def scan(self) -> LegacyImportStageResult:
        return LegacyFileScanner().scan_sources()

    def sanitize(self) -> LegacyImportStageResult:
        return LegacySanitizationService().sanitize_inventory()

    def classify(self) -> LegacyImportStageResult:
        return LegacyClassificationService().classify()

    def detect_conflicts(self) -> LegacyImportStageResult:
        return LegacyConflictDetectionService().detect()

    def review_summary(self) -> LegacyImportStageResult:
        return LegacyReviewService().summarize_review()

    def import_preview(self) -> LegacyImportStageResult:
        return LegacyReviewService().import_preview()

    def commit(self, approval_manifest: Path) -> LegacyImportStageResult:
        return LegacyReviewService().commit(approval_manifest)

    def run_stage(self, stage: str) -> LegacyImportStageResult:
        stages = {
            "scan": self.scan,
            "sanitize": self.sanitize,
            "classify": self.classify,
            "conflicts": self.detect_conflicts,
            "review": self.review_summary,
            "import-preview": self.import_preview,
        }
        if stage not in stages:
            return LegacyImportStageResult(status="error", stage=stage, warnings=["unknown_stage"])
        return stages[stage]()

    def status(self) -> LegacyRAGStatus:
        ensure_dirs()
        committed = False
        manifest: dict[str, object] = {}
        if PATHS43.namespace_manifest.exists():
            manifest = json.loads(PATHS43.namespace_manifest.read_text(encoding="utf-8"))
            committed = bool(manifest.get("committed"))
        counts = {
            "inventory": len(read_jsonl(PATHS43.inventory)),
            "quarantine": len(read_jsonl(PATHS43.quarantine)),
            "sanitized_chunks": len(read_jsonl(PATHS43.sanitized)),
            "classified_chunks": len(read_jsonl(PATHS43.classified)),
            "conflicts": len(read_jsonl(PATHS43.conflicts)),
            "approved": len(read_jsonl(BASE / "approved" / "legacy_human_approved_chunks.jsonl")) or len(read_jsonl(PATHS43.approved)),
            "rejected": len(read_jsonl(PATHS43.rejected)),
            "regression_candidates": len(read_jsonl(PATHS43.regressions)),
            "lesson_candidates": len(read_jsonl(PATHS43.lessons)),
        }
        status = "ok" if counts["inventory"] else "not_scanned"
        if not committed:
            status = "preview_only" if counts["approved"] else status
        return LegacyRAGStatus(status=status, namespace_id=NAMESPACE_ID, namespace_committed=committed, counts=counts, artifacts={"base": str(BASE), "namespace": str(NAMESPACE_DIR), "manifest": str(PATHS43.namespace_manifest)})

    def chunks(self) -> list[dict[str, object]]:
        return read_jsonl(PATHS43.approved)

    def chunk(self, chunk_id: str) -> dict[str, object] | None:
        for row in self.chunks() + read_jsonl(PATHS43.classified):
            if row.get("chunk_id") == chunk_id:
                return row
        return None

    def conflicts(self) -> list[dict[str, object]]:
        return read_jsonl(PATHS43.conflicts)

    def regression_candidates(self) -> list[dict[str, object]]:
        return read_jsonl(PATHS43.regressions)

    def lesson_candidates(self) -> list[dict[str, object]]:
        return read_jsonl(PATHS43.lessons)


def cli_preview() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["scan", "sanitize", "classify", "conflicts", "review", "import-preview"])
    args = parser.parse_args()
    result = LegacyRAGPipelineService().run_stage(args.stage)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return 0 if result.status in {"ok", "needs_approval"} else 1


def cli_review_summary() -> int:
    result = LegacyRAGPipelineService().review_summary()
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return 0 if result.status == "ok" else 1


def cli_commit() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval-manifest", required=True)
    args = parser.parse_args()
    result = LegacyRAGPipelineService().commit(Path(args.approval_manifest))
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return 0 if result.status == "ok" else 2



