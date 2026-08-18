from __future__ import annotations

import json
import re
from typing import Any

from aipinho.schemas.evaluation.contract_validation_result import ContractValidationResult


class JSONOutputValidator:
    def _extract_json_candidate(self, content: str, *, allow_markdown_fence: bool) -> str:
        text = content.strip()
        if allow_markdown_fence:
            match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return text

    def validate(
        self,
        content: str,
        *,
        required_fields: list[str] | None = None,
        allow_markdown_fence: bool = True,
        reject_trailing_text: bool = False,
        contract_type: str = "json",
    ) -> ContractValidationResult:
        required_fields = required_fields or []
        candidate = self._extract_json_candidate(content, allow_markdown_fence=allow_markdown_fence)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            return ContractValidationResult(
                valid=False,
                format_valid=False,
                contract_type=contract_type,
                expected_format="json",
                detected_format="text",
                required_fields=required_fields,
                violations=["invalid_json"],
                warnings=[f"invalid_json:{exc.msg}"],
            )
        if reject_trailing_text and candidate != content.strip():
            return ContractValidationResult(
                valid=False,
                format_valid=True,
                contract_type=contract_type,
                expected_format="json",
                detected_format="json",
                required_fields=required_fields,
                parsed_json=parsed,
                violations=["trailing_text_after_json"],
            )
        missing: list[str] = []
        if isinstance(parsed, dict):
            missing = [field for field in required_fields if field not in parsed]
        elif required_fields:
            missing = list(required_fields)
        return ContractValidationResult(
            valid=not missing,
            format_valid=True,
            contract_type=contract_type,
            expected_format="json",
            detected_format="json",
            required_fields=required_fields,
            missing_fields=missing,
            parsed_json=parsed,
            violations=["missing_required_field:" + field for field in missing],
        )
