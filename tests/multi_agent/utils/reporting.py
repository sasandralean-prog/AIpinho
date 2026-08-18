from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{20,}"),
    re.compile(r"Bearer\s+[0-9A-Za-z_\-\.]{10,}", re.IGNORECASE),
    re.compile(r"Qswis[0-9A-Za-z_\-]{10,}"),
]


def redact_text(value: str) -> str:
    output = value
    for pattern in SECRET_PATTERNS:
        output = pattern.sub("[REDACTED_SECRET]", output)
    return output


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def write_regression_report(report_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = payload.get("timestamp") or utc_timestamp()
    payload["timestamp"] = timestamp
    json_path = report_dir / f"multi_agent_regression_{timestamp}.json"
    md_path = report_dir / f"multi_agent_regression_{timestamp}.md"
    sanitized = json.loads(redact_text(json.dumps(payload, ensure_ascii=False)))
    json_path.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(sanitized), encoding="utf-8")
    return md_path, json_path


def _markdown(payload: dict[str, Any]) -> str:
    command = " ".join(payload.get("command", []))
    return "\n".join(
        [
            "# Multi-Agent Regression Report",
            "",
            f"- Timestamp: `{payload.get('timestamp')}`",
            f"- Mode: `{payload.get('mode')}`",
            f"- Exit code: `{payload.get('exit_code')}`",
            f"- Duration seconds: `{payload.get('duration_seconds')}`",
            f"- Command: `{command}`",
            f"- Passed marker found: `{payload.get('passed_marker_found')}`",
            f"- Failed marker found: `{payload.get('failed_marker_found')}`",
            "",
            "## Suites",
            "",
            *(f"- `{item}`" for item in payload.get("suites", [])),
            "",
            "## Output Tail",
            "",
            "```text",
            payload.get("output_tail", ""),
            "```",
            "",
            "## Recommendations",
            "",
            *(f"- {item}" for item in payload.get("recommendations", [])),
        ]
    )

