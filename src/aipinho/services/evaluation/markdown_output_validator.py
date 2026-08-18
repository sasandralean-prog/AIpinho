from __future__ import annotations

import re

from aipinho.schemas.evaluation.contract_validation_result import ContractValidationResult


class MarkdownOutputValidator:
    def _normalize(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower().replace("_", " ")).strip()

    def _has_section(self, content: str, section: str) -> bool:
        normalized = self._normalize(section)
        lines = content.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and self._normalize(stripped.lstrip("#").strip()) == normalized:
                return True
        return normalized in self._normalize(content)

    def validate(self, content: str, *, required_sections: list[str] | None = None, contract_type: str = "markdown") -> ContractValidationResult:
        required_sections = required_sections or []
        if not content.strip():
            return ContractValidationResult(
                valid=False,
                format_valid=False,
                contract_type=contract_type,
                expected_format="markdown",
                detected_format="empty",
                required_sections=required_sections,
                violations=["empty_response"],
            )
        missing = [section for section in required_sections if not self._has_section(content, section)]
        return ContractValidationResult(
            valid=not missing,
            format_valid=True,
            contract_type=contract_type,
            expected_format="markdown",
            detected_format="markdown",
            required_sections=required_sections,
            missing_sections=missing,
            violations=["missing_required_section:" + section for section in missing],
        )
