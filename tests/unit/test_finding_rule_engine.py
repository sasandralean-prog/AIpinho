from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.services.reports.evidence_extractor import EvidenceExtractor
from aipinho.services.reports.evidence_index_service import EvidenceIndexService
from aipinho.services.reports.finding_rule_engine import FindingRuleEngine


def _context():
    tree = ProjectTreeSummary(workspace="w", status="ok", candidate_files=["src/app.py", "config/policies/p.yaml"], ignored_paths=["pkg/__pycache__"])
    bundle = FileContextBundle(bundle_id="b", workspace="w", status="ok", items=[FileContextItem(path="src/app.py", status="included", content="from fastapi import FastAPI"), FileContextItem(path="config/policies/p.yaml", status="included", content="schema_version: 1")])
    extractor = EvidenceExtractor()
    evidence = [*extractor.extract_from_tree(tree), *extractor.extract_from_file_context(bundle)]
    return tree, bundle, EvidenceIndexService(evidence)


def test_finding_rule_engine_supports_core_operators_and_requires_evidence():
    rules = {"rules": {
        "any_exists": {"category": "architecture", "severity": "info", "when": {"any_paths_exist": ["src/**/*.py"]}, "title": "src exists", "recommendation": "review"},
        "low_tests": {"category": "test", "severity": "medium", "when": {"path_count_less_than": {"pattern": "tests/**/*.py", "count": 1}}, "title": "tests low", "recommendation": "add tests"},
        "all_policy_no_tests": {"category": "policy", "severity": "medium", "when": {"all": [{"any_paths_exist": ["config/policies/*.yaml"]}, {"not_any_paths_exist": ["tests/**/*policy*.py"]}]}, "title": "policy no tests", "recommendation": "add policy tests"},
        "contains_fastapi": {"category": "routing", "severity": "info", "when": {"file_contains": {"pattern": "src/**/*.py", "contains": ["FastAPI"]}}, "title": "contains fastapi", "recommendation": "document routes"},
        "no_evidence": {"category": "risk", "severity": "critical", "when": {"any_paths_exist": ["missing/**/*.py"]}, "title": "should not emit", "recommendation": "none"},
    }}
    tree, bundle, index = _context()
    findings = FindingRuleEngine(rules_config=rules).evaluate_rules(tree, bundle, index)
    titles = [item.title for item in findings]

    assert "src exists" in titles
    assert "tests low" in titles
    assert "policy no tests" in titles
    assert "contains fastapi" in titles
    assert "should not emit" not in titles
    assert all(item.evidence for item in findings)
    findings_again = FindingRuleEngine(rules_config=rules).evaluate_rules(tree, bundle, index)
    assert [(item.title, item.category, item.severity) for item in findings] == [(item.title, item.category, item.severity) for item in findings_again]
