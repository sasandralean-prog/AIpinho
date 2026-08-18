from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectAnalysisBudget:
    max_total_seconds: float = 300.0
    max_files_scanned: int = 500
    max_files_read: int = 12
    max_bytes_read: int = 120_000
    max_output_bytes: int = 1_000_000
    cancel_poll_interval: int = 50
    allow_partial_result: bool = True

    @classmethod
    def from_environment(cls) -> "ProjectAnalysisBudget":
        return cls(
            max_total_seconds=float(os.environ.get("AIPINHO_PROJECT_ANALYSIS_MAX_SECONDS", "300")),
            max_files_scanned=int(os.environ.get("AIPINHO_PROJECT_ANALYSIS_MAX_FILES_SCANNED", "500")),
            max_files_read=int(os.environ.get("AIPINHO_PROJECT_ANALYSIS_MAX_FILES_READ", "12")),
            max_bytes_read=int(os.environ.get("AIPINHO_PROJECT_ANALYSIS_MAX_BYTES_READ", "120000")),
            max_output_bytes=int(os.environ.get("AIPINHO_PROJECT_ANALYSIS_MAX_OUTPUT_BYTES", "1000000")),
            cancel_poll_interval=int(os.environ.get("AIPINHO_PROJECT_ANALYSIS_CANCEL_POLL_INTERVAL", "50")),
            allow_partial_result=str(os.environ.get("AIPINHO_PROJECT_ANALYSIS_ALLOW_PARTIAL", "true")).casefold()
            in {"1", "true", "yes", "sim"},
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "max_total_seconds": self.max_total_seconds,
            "max_files_scanned": self.max_files_scanned,
            "max_files_read": self.max_files_read,
            "max_bytes_read": self.max_bytes_read,
            "max_output_bytes": self.max_output_bytes,
            "cancel_poll_interval": self.cancel_poll_interval,
            "allow_partial_result": self.allow_partial_result,
        }
