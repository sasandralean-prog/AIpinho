from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent


@pytest.mark.multi_agent
def test_regression_matrices_are_parseable_and_cover_required_domains():
    required = {
        "golden_path_matrix.yaml": {"aipinho_simple_chat", "artifact_upload_download", "self_healing_low_risk"},
        "freedom_regression_matrix.yaml": {"read_workspace_autoapproved", "build_shell_allowed", "safe_codex_prompt_without_excessive_approval"},
        "security_regression_matrix.yaml": {"destructive_shell_blocked", "token_in_url_blocked", "raw_hidden_by_default"},
        "speaker_truth_matrix.yaml": {"validation_failed_blocks_clean_completed", "artifact_generated_requires_artifact_id"},
        "memory_regression_matrix.yaml": {"memory_candidate_lifecycle", "secrets_not_saved_to_memory", "memory_absence_does_not_block_safe_task"},
    }
    for filename, expected in required.items():
        payload = yaml.safe_load((ROOT / filename).read_text(encoding="utf-8"))
        assert payload["version"] == 1
        cases = payload["cases"]
        case_ids = {case["id"] if isinstance(case, dict) else case for case in cases}
        assert expected <= case_ids


@pytest.mark.multi_agent
def test_matrix_files_do_not_embed_secrets_or_user_specific_paths():
    banned = ["AIza", "sk-", "Qswis", "PinhoForge", "PinhoForgeStudio", "C:\\Users\\rafae\\"]
    for path in ROOT.glob("*_matrix.yaml"):
        text = path.read_text(encoding="utf-8")
        for item in banned:
            assert item not in text


@pytest.mark.multi_agent
def test_memory_matrix_requirements_are_present():
    text = "\n".join((ROOT / filename).read_text(encoding="utf-8") for filename in ["golden_path_matrix.yaml", "speaker_truth_matrix.yaml", "memory_regression_matrix.yaml"])
    assert "memory" in text.lower()
    assert "evidence" in text.lower()
