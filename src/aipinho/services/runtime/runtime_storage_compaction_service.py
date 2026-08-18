from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.runtime.task_run_store import TaskRunStore


class RuntimeStorageCompactionService:
    """Governed storage projection and compaction for TaskRun records.

    The service never deletes evidence. It rewrites run.json through
    TaskRunStore's lightweight payload path, creates run_index.json projections,
    and leaves result/events/artifact refs in place.
    """

    def __init__(
        self,
        *,
        store: TaskRunStore | None = None,
        reports_root: Path | None = None,
        large_run_threshold_bytes: int = 1_000_000,
    ) -> None:
        self.store = store or TaskRunStore()
        self.reports_root = reports_root or (PATHS.reports_root / "runtime_consolidation")
        self.large_run_threshold_bytes = max(1, int(large_run_threshold_bytes))

    def compact_task_runs(
        self,
        *,
        threshold_bytes: int | None = None,
        limit: int = 1000,
        write_report: bool = True,
        report_name: str = "runtime_storage_compaction_report.json",
    ) -> dict[str, Any]:
        threshold = max(1, int(threshold_bytes or self.large_run_threshold_bytes))
        run_dirs = self._run_dirs(limit=limit)
        candidates: list[Path] = []
        before_total = 0
        for run_dir in run_dirs:
            run_path = run_dir / "run.json"
            size = run_path.stat().st_size if run_path.exists() else 0
            before_total += size
            if size >= threshold or not (run_dir / "run_index.json").exists():
                candidates.append(run_dir)

        results: list[dict[str, Any]] = []
        for run_dir in candidates:
            try:
                results.append(self.store.compact_run_storage(run_dir.name))
            except Exception as exc:
                results.append(
                    {
                        "run_id": run_dir.name,
                        "status": "failed",
                        "error": repr(exc),
                        "before_bytes": (run_dir / "run.json").stat().st_size if (run_dir / "run.json").exists() else 0,
                        "after_bytes": (run_dir / "run.json").stat().st_size if (run_dir / "run.json").exists() else 0,
                        "valid_json": False,
                        "index_written": (run_dir / "run_index.json").exists(),
                    }
                )

        after_total = sum((run_dir / "run.json").stat().st_size for run_dir in run_dirs if (run_dir / "run.json").exists())
        payload = {
            "status": "ok" if not any(item.get("status") == "failed" for item in results) else "degraded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "threshold_bytes": threshold,
            "run_dirs_seen": len(run_dirs),
            "candidates_seen": len(candidates),
            "files_compacted": sum(1 for item in results if item.get("status") in {"compacted", "rewritten", "indexed"}),
            "total_before_bytes": before_total,
            "total_after_bytes": after_total,
            "total_saved_bytes": max(0, before_total - after_total),
            "deletes_evidence": False,
            "preserves_result_json": True,
            "preserves_events_json": True,
            "uses_payload_refs": True,
            "results": results,
        }
        if write_report:
            self.reports_root.mkdir(parents=True, exist_ok=True)
            (self.reports_root / report_name).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            payload["report_path"] = str(self.reports_root / report_name)
        return payload

    def projection_health(self, *, limit: int = 1000) -> dict[str, Any]:
        run_dirs = self._run_dirs(limit=limit)
        missing_index = []
        large_runs = []
        for run_dir in run_dirs:
            run_path = run_dir / "run.json"
            size = run_path.stat().st_size if run_path.exists() else 0
            if not (run_dir / "run_index.json").exists():
                missing_index.append(run_dir.name)
            if size >= self.large_run_threshold_bytes:
                large_runs.append({"run_id": run_dir.name, "size_bytes": size})
        return {
            "status": "degraded" if missing_index or large_runs else "ok",
            "run_dirs_seen": len(run_dirs),
            "missing_index_count": len(missing_index),
            "missing_index_run_ids": missing_index[:50],
            "large_run_count": len(large_runs),
            "large_runs": sorted(large_runs, key=lambda item: int(item["size_bytes"]), reverse=True)[:50],
            "threshold_bytes": self.large_run_threshold_bytes,
        }

    def _run_dirs(self, *, limit: int) -> list[Path]:
        if not self.store.root.exists():
            return []
        return sorted(
            [path for path in self.store.root.glob("task_run_*") if path.is_dir()],
            key=lambda path: (path / "run.json").stat().st_mtime if (path / "run.json").exists() else 0,
            reverse=True,
        )[: max(1, min(limit, 5000))]

