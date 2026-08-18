from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.evidence_finding import EvidenceFinding
from aipinho.services.reports.evidence_extractor import EvidenceExtractor
from aipinho.services.reports.evidence_index_service import EvidenceIndexService, matches_path
from aipinho.services.reports.report_trace_service import ReportTraceService
from aipinho.services.reports.severity_classifier import SeverityClassifier
from aipinho.services.analysis.project_profile_service import ProjectProfileService
from aipinho.utils.yaml_loader import load_yaml_file


class FindingRuleEngine:
    def __init__(self, rules_config: dict[str, Any] | None = None, severity: SeverityClassifier | None = None, extractor: EvidenceExtractor | None = None) -> None:
        self.rules_config = rules_config or load_yaml_file(PATHS.config_root / "reports" / "finding_rules.yaml", critical=True, root=PATHS.config_root / "reports")
        self.severity = severity or SeverityClassifier()
        self.extractor = extractor or EvidenceExtractor()
        self.trace = ReportTraceService()
        self.profiles = ProjectProfileService()
        evidence_policy = load_yaml_file(PATHS.config_root / "reports" / "evidence_policy.yaml", critical=True, root=PATHS.config_root / "reports")
        self.max_evidence = int(evidence_policy.get("evidence", {}).get("max_evidence_per_finding", 5) if isinstance(evidence_policy.get("evidence", {}), dict) else 5)

    def load_rules(self) -> dict[str, Any]:
        value = self.rules_config.get("rules", {})
        return value if isinstance(value, dict) else {}

    def evaluate_rules(self, project_tree: ProjectTreeSummary, context_bundle: FileContextBundle, evidence_index: EvidenceIndexService) -> list[EvidenceFinding]:
        findings: list[EvidenceFinding] = []
        context = {"tree": project_tree, "bundle": context_bundle, "index": evidence_index, "paths": evidence_index.paths()}
        for rule_id, rule in self.load_rules().items():
            if not isinstance(rule, dict):
                continue
            finding = self.evaluate_rule(str(rule_id), rule, context)
            if finding is not None:
                findings.append(finding)
        return sorted(findings, key=lambda item: (item.category, item.title, item.finding_id))

    def evaluate_rule(self, rule_id: str, rule: dict[str, Any], context: dict[str, Any]) -> EvidenceFinding | None:
        condition = rule.get("when", {})
        matched, evidence = self._evaluate_condition(condition, context)
        evidence = self._dedupe(evidence)[: self.max_evidence]
        if not matched or not evidence:
            return None
        requested_severity = str(rule.get("severity", "info"))
        severity, confidence = self.severity.classify(requested_severity, evidence)
        title = str(rule.get("title", rule_id.replace("_", " ")))
        inference = str(rule.get("inference", "Inferencia baseada em evidencia deterministica."))
        recommendation = str(rule.get("recommendation", "Registrar acompanhamento futuro com teste e evidencia."))
        return EvidenceFinding(
            finding_id=f"finding_{uuid5(NAMESPACE_URL, rule_id + ':' + title).hex}",
            title=title,
            category=str(rule.get("category", "risk")),
            severity=severity,
            confidence=confidence,
            summary=f"Regra deterministica aplicada: {rule_id}.",
            evidence=evidence,
            inference=inference,
            recommendation=recommendation,
            requires_write=False,
            requires_followup=False,
            trace=[self.trace.item("finding_rule_engine", "matched", "rule_matched", rule_id=rule_id, source="config/reports/finding_rules.yaml", data={"evidence_count": len(evidence), "requested_severity": requested_severity})],
        )

    def attach_evidence(self, rule: dict[str, Any], context: dict[str, Any]) -> list[EvidenceCitation]:
        matched, evidence = self._evaluate_condition(rule.get("when", {}), context)
        return self._dedupe(evidence) if matched else []

    def _evaluate_condition(self, condition: Any, context: dict[str, Any]) -> tuple[bool, list[EvidenceCitation]]:
        if not isinstance(condition, dict):
            return False, []
        if "all" in condition:
            evidence: list[EvidenceCitation] = []
            for item in condition.get("all", []) or []:
                matched, item_evidence = self._evaluate_condition(item, context)
                if not matched:
                    return False, []
                evidence.extend(item_evidence)
            return True, evidence
        if "any" in condition:
            evidence: list[EvidenceCitation] = []
            any_matched = False
            for item in condition.get("any", []) or []:
                matched, item_evidence = self._evaluate_condition(item, context)
                if matched:
                    any_matched = True
                    evidence.extend(item_evidence)
            return any_matched, evidence
        if "any_paths_exist" in condition:
            patterns = [str(item) for item in condition.get("any_paths_exist", []) or []]
            evidence = self._evidence_for_patterns(patterns, context)
            return bool(evidence), evidence
        if "not_any_paths_exist" in condition:
            patterns = [str(item) for item in condition.get("not_any_paths_exist", []) or []]
            existing = self._evidence_for_patterns(patterns, context)
            if existing:
                return False, []
            evidence = [self.extractor.extract_absence_evidence(pattern, context.get("tree")) for pattern in patterns]
            return True, evidence
        if "path_count_less_than" in condition:
            spec = condition.get("path_count_less_than") or {}
            if not isinstance(spec, dict):
                return False, []
            pattern = str(spec.get("pattern", ""))
            count = int(spec.get("count", 0) or 0)
            evidence = self._evidence_for_patterns([pattern], context)
            if len({item.path for item in evidence if item.path}) < count:
                absence = self.extractor.extract_absence_evidence(pattern, context.get("tree"))
                return True, [*evidence, absence]
            return False, []
        if "profile_test_count_less_than" in condition:
            spec = condition.get("profile_test_count_less_than") or {}
            if not isinstance(spec, dict):
                return False, []
            count = int(spec.get("count", 0) or 0)
            tree = context.get("tree")
            if tree is None:
                return False, []
            patterns = self.profiles.test_patterns(tree)
            evidence = self._evidence_for_patterns(patterns, context)
            matched_paths = {item.path for item in evidence if item.path}
            if len(matched_paths) >= count:
                return False, []
            profile_ids = self.profiles.detect(tree)
            if not profile_ids:
                return False, []
            absence = [
                self.extractor.extract_absence_evidence(pattern, tree)
                for pattern in patterns[:3]
            ]
            return True, [*evidence, *absence]
        if "path_count_greater_than" in condition:
            spec = condition.get("path_count_greater_than") or {}
            if not isinstance(spec, dict):
                return False, []
            pattern = str(spec.get("pattern", ""))
            count = int(spec.get("count", 0) or 0)
            evidence = self._evidence_for_patterns([pattern], context)
            return len({item.path for item in evidence if item.path}) > count, evidence
        if "file_contains" in condition:
            spec = condition.get("file_contains") or {}
            if not isinstance(spec, dict):
                return False, []
            return self._file_contains(str(spec.get("pattern", "")), [str(item) for item in spec.get("contains", []) or []], context)
        if "config_key_exists" in condition:
            spec = condition.get("config_key_exists") or {}
            if isinstance(spec, str):
                spec = {"path": spec, "key": ""}
            return self._config_key_exists(str(spec.get("path", "")), str(spec.get("key", "")), context)
        if "absence" in condition:
            pattern = str(condition.get("absence"))
            existing = self._evidence_for_patterns([pattern], context)
            if existing:
                return False, []
            return True, [self.extractor.extract_absence_evidence(pattern, context.get("tree"))]
        return False, []

    def _evidence_for_patterns(self, patterns: list[str], context: dict[str, Any]) -> list[EvidenceCitation]:
        index: EvidenceIndexService = context["index"]
        evidence: list[EvidenceCitation] = []
        for pattern in patterns:
            evidence.extend(index.find_by_pattern(pattern))
        return self._dedupe(evidence)

    def _file_contains(self, pattern: str, contains: list[str], context: dict[str, Any]) -> tuple[bool, list[EvidenceCitation]]:
        bundle: FileContextBundle = context["bundle"]
        index: EvidenceIndexService = context["index"]
        evidence: list[EvidenceCitation] = []
        lowered_needles = [item.lower() for item in contains]
        for item in bundle.items:
            if not item.content or not matches_path(item.path, pattern):
                continue
            if any(needle in item.content.lower() for needle in lowered_needles):
                evidence.extend(index.find_by_path(item.path))
        return bool(evidence), self._dedupe(evidence)

    def _config_key_exists(self, pattern: str, key: str, context: dict[str, Any]) -> tuple[bool, list[EvidenceCitation]]:
        bundle: FileContextBundle = context["bundle"]
        index: EvidenceIndexService = context["index"]
        for item in bundle.items:
            if not item.content or not matches_path(item.path, pattern):
                continue
            if key and key in item.content:
                return True, index.find_by_path(item.path)
        return False, []

    def _dedupe(self, evidence: list[EvidenceCitation]) -> list[EvidenceCitation]:
        seen: set[str] = set()
        result: list[EvidenceCitation] = []
        for item in evidence:
            if item.evidence_id in seen:
                continue
            seen.add(item.evidence_id)
            result.append(item)
        return sorted(result, key=lambda item: (item.path or "", item.source_type, item.evidence_id))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "finding_rule_engine", "rules": len(self.load_rules())}
