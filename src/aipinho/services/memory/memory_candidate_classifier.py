from __future__ import annotations


class MemoryCandidateClassifier:
    ALLOWED = {
        "architecture_decision",
        "policy_decision",
        "validation_learning",
        "bug_fix_summary",
        "patch_outcome",
        "runtime_behavior",
        "project_constraint",
        "user_instruction",
        "operational_procedure",
        "known_limitation",
        "testing_guidance",
        "risk_pattern",
        "design_rationale",
    }

    def classify(self, text: str, requested_kind: str | None = None) -> str:
        if requested_kind in self.ALLOWED:
            return requested_kind
        lowered = text.lower()
        if "quality gate" in lowered or "policy" in lowered or "approval" in lowered:
            return "policy_decision"
        if "validation" in lowered or "teste" in lowered or "test" in lowered:
            return "validation_learning"
        if "patch" in lowered and ("appl" in lowered or "rollback" in lowered):
            return "patch_outcome"
        if "limitation" in lowered or "limita" in lowered:
            return "known_limitation"
        if "risco" in lowered or "risk" in lowered or "bloque" in lowered:
            return "risk_pattern"
        if "guarde" in lowered or "lembre" in lowered or "memoria" in lowered or "memória" in lowered:
            return "user_instruction"
        return "runtime_behavior"
