from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.multi_agent.utils.reporting import redact_text, write_regression_report


SUITE_ARGS = {
    "golden_paths": ["tests/multi_agent/golden_paths"],
    "security": ["tests/multi_agent/security"],
    "freedom": ["tests/multi_agent/freedom"],
    "speaker_truth": ["tests/multi_agent/speaker_truth"],
    "memory": ["tests/learning", "tests/multi_agent/test_regression_matrices.py"],
    "learning": ["tests/learning"],
    "delegation": ["tests/multi_agent/golden_paths/test_multi_agent_golden_paths.py"],
    "tool_gateway": ["tests/multi_agent/golden_paths/test_multi_agent_golden_paths.py"],
    "ui_contracts": ["tests/multi_agent/ui_contracts"],
    "self_healing": ["tests/multi_agent/self_healing"],
    "multimodal": ["tests/multi_agent/multimodal"],
    "artifacts": ["tests/multi_agent/golden_paths/test_multi_agent_golden_paths.py"],
    "project_profiles": ["tests/multi_agent/project_profiles"],
    "skills": ["tests/skills", "tests/multi_agent/skills"],
    "sandbox": ["tests/sandbox", "tests/multi_agent/sandbox"],
    "project_factory": ["tests/project_factory"],
    "autopilot": ["tests/autopilot"],
    "workspaces": ["tests/workspaces"],
    "promotion": ["tests/promotion"],
    "templates": ["tests/templates"],
    "artifact_library": ["tests/artifact_library"],
    "skill_packs": ["tests/skill_packs"],
    "workflows": ["tests/workflows"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AIpinho multi-agent regression suites.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--golden-paths", action="store_true")
    parser.add_argument("--security", action="store_true")
    parser.add_argument("--freedom", action="store_true")
    parser.add_argument("--speaker-truth", action="store_true")
    parser.add_argument("--memory", action="store_true")
    parser.add_argument("--learning", action="store_true")
    parser.add_argument("--delegation", action="store_true")
    parser.add_argument("--tool-gateway", action="store_true")
    parser.add_argument("--ui-contracts", action="store_true")
    parser.add_argument("--self-healing", action="store_true")
    parser.add_argument("--multimodal", action="store_true")
    parser.add_argument("--artifacts", action="store_true")
    parser.add_argument("--project-profiles", action="store_true")
    parser.add_argument("--skills", action="store_true")
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--project-factory", action="store_true")
    parser.add_argument("--autopilot", action="store_true")
    parser.add_argument("--workspaces", action="store_true")
    parser.add_argument("--promotion", action="store_true")
    parser.add_argument("--templates", action="store_true")
    parser.add_argument("--artifact-library", action="store_true")
    parser.add_argument("--skill-packs", action="store_true")
    parser.add_argument("--workflows", action="store_true")
    parser.add_argument("--report-dir", default=str(ROOT / "reports" / "regression"))
    return parser.parse_args()


def selected_suites(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(SUITE_ARGS)
    if args.quick:
        return ["golden_paths", "security", "freedom", "speaker_truth", "ui_contracts", "self_healing"]
    selected = []
    for suite in SUITE_ARGS:
        attr = suite.replace("_", "-")
        if getattr(args, attr.replace("-", "_")):
            selected.append(suite)
    return selected or ["golden_paths", "security", "freedom", "speaker_truth"]


def main() -> int:
    args = parse_args()
    suites = selected_suites(args)
    targets: list[str] = []
    for suite in suites:
        for item in SUITE_ARGS[suite]:
            if item not in targets:
                targets.append(item)
    command = [sys.executable, "-m", "pytest", *targets, "-q"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    env["AIPINHO_MULTI_AGENT_REGRESSION"] = "1"
    start = time.time()
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    duration = round(time.time() - start, 3)
    combined = redact_text((completed.stdout or "") + "\n" + (completed.stderr or ""))
    payload = {
        "mode": "all" if args.all else "quick" if args.quick else "selected",
        "suites": suites,
        "command": command,
        "exit_code": completed.returncode,
        "duration_seconds": duration,
        "passed_marker_found": " passed" in combined or "passed in" in combined,
        "failed_marker_found": " failed" in combined or "FAILED" in combined,
        "output_tail": combined[-6000:],
        "recommendations": [
            "Run --all before release certification when time allows.",
            "Keep provider tests on fake adapters unless manually opted into real inference.",
            "Promote new production bugs into this suite before expanding features.",
        ],
    }
    md_path, json_path = write_regression_report(Path(args.report_dir), payload)
    print(combined)
    print(f"\nReports:\n- {md_path}\n- {json_path}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
