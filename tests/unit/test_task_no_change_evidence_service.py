from aipinho.services.runtime.task_no_change_evidence_service import TaskNoChangeEvidenceService


def test_no_change_evidence_uses_prior_report_verdict(tmp_path):
    workspace = tmp_path / "workspace"
    reports = workspace / "reports"
    reports.mkdir(parents=True)
    (reports / "diagnosis.md").write_text(
        "Titulo\nDiagnostico\n\nVeredito\nno_changes_needed\n\nResumo\nTudo ja esta satisfeito.\n",
        encoding="utf-8",
    )

    evidence = TaskNoChangeEvidenceService().evaluate(
        prompt="Com base no diagnostico anterior, implemente correcao minima se necessario.",
        workspace=str(workspace),
    )

    assert evidence is not None
    assert evidence.status == "no_changes_needed"
    assert evidence.reason_code == "prior_diagnostic_indicates_no_patch_needed"
    assert evidence.report_path == "reports/diagnosis.md"


def test_no_change_evidence_rejects_negative_verdict(tmp_path):
    workspace = tmp_path / "workspace"
    reports = workspace / "reports"
    reports.mkdir(parents=True)
    (reports / "diagnosis.md").write_text(
        "Veredito: persistence_fake_demo_only\n",
        encoding="utf-8",
    )

    evidence = TaskNoChangeEvidenceService().evaluate(
        prompt="Com base no diagnostico anterior, implemente correcao minima.",
        workspace=str(workspace),
    )

    assert evidence is None


def test_no_change_evidence_ignores_derived_no_change_report(tmp_path):
    workspace = tmp_path / "workspace"
    reports = workspace / "reports"
    reports.mkdir(parents=True)
    (reports / "fix.md").write_text(
        "Status\nno_changes_needed\n\nVeredito\npersistence_real\n",
        encoding="utf-8",
    )
    (reports / "diagnosis.md").write_text(
        "Status\ncompleted\n\nVeredito\npersistence_real\n\nResumo\nPersistencia confirmada.\n",
        encoding="utf-8",
    )
    config = {
        "evidence": {
            "report_dirs": ["reports"],
            "excluded_report_statuses": ["no_changes_needed"],
            "max_reports": 12,
            "max_bytes_per_report": 200000,
            "prompt_reference_terms": ["diagnostico anterior"],
            "completion_request_terms": ["implemente"],
            "positive_verdicts": ["persistence_real"],
            "negative_verdict_fragments": [],
        }
    }

    evidence = TaskNoChangeEvidenceService(config=config).evaluate(
        prompt="Com base no diagnostico anterior, implemente a correcao.",
        workspace=str(workspace),
    )

    assert evidence is not None
    assert evidence.report_path == "reports/diagnosis.md"
