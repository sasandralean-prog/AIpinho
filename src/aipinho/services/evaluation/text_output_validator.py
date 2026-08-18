from __future__ import annotations

from aipinho.schemas.evaluation.contract_validation_result import ContractValidationResult


class TextOutputValidator:
    def validate(self, content: str, *, contract_type: str = "plain_text", max_empty_ratio: float = 0.8) -> ContractValidationResult:
        text = content or ""
        if not text.strip():
            return ContractValidationResult(
                valid=False,
                format_valid=False,
                contract_type=contract_type,
                expected_format="text",
                detected_format="empty",
                violations=["empty_response"],
            )
        empty_ratio = 0.0 if not text else sum(1 for char in text if char.isspace()) / max(1, len(text))
        warnings = ["high_empty_ratio"] if empty_ratio > max_empty_ratio else []
        return ContractValidationResult(
            valid=True,
            format_valid=True,
            contract_type=contract_type,
            expected_format="text",
            detected_format="text",
            warnings=warnings,
        )
