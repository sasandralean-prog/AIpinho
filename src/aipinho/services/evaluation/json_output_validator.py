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
        json_shape: Any | None = None,
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
        shape_violations = self._shape_violations(
            parsed,
            json_shape,
            path="",
        )
        return ContractValidationResult(
            valid=not missing and not shape_violations,
            format_valid=True,
            contract_type=contract_type,
            expected_format="json",
            detected_format="json",
            required_fields=required_fields,
            missing_fields=missing,
            parsed_json=parsed,
            violations=[
                *["missing_required_field:" + field for field in missing],
                *shape_violations,
            ],
        )

    def _shape_violations(
        self,
        value: Any,
        schema: Any,
        *,
        path: str,
    ) -> list[str]:
        if schema is None:
            return []
        label = path or "root"
        if isinstance(schema, str):
            if schema == "non_empty_string":
                if not isinstance(value, str):
                    return [f"schema_type_mismatch:{label}"]
                return [] if value.strip() else [f"schema_non_empty_mismatch:{label}"]
            if schema == "number_between_0_and_1":
                valid = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and 0 <= float(value) <= 1
                )
                return [] if valid else [f"schema_type_mismatch:{label}"]
            if schema == "boolean":
                return [] if isinstance(value, bool) else [f"schema_type_mismatch:{label}"]
            if schema == "list[string]":
                valid = isinstance(value, list) and all(isinstance(item, str) for item in value)
                return [] if valid else [f"schema_type_mismatch:{label}"]
            if schema == "object[string,list[scalar]]":
                scalar = (bool, int, float, str)
                valid = isinstance(value, dict) and all(
                    isinstance(key, str)
                    and isinstance(items, list)
                    and all(isinstance(item, scalar) for item in items)
                    for key, items in value.items()
                )
                return [] if valid else [f"schema_type_mismatch:{label}"]
            return [] if isinstance(value, str) else [f"schema_type_mismatch:{label}"]

        if isinstance(schema, list):
            if not isinstance(value, list):
                return [f"schema_type_mismatch:{label}"]
            if not schema:
                return []
            item_schema = schema[0]
            violations: list[str] = []
            for index, item in enumerate(value):
                item_path = f"{path}[{index}]" if path else f"[{index}]"
                violations.extend(
                    self._shape_violations(item, item_schema, path=item_path)
                )
            return violations

        if not isinstance(schema, dict):
            return []

        schema_type = str(schema.get("type") or "").strip().casefold()
        if schema_type:
            if schema_type == "string":
                if not isinstance(value, str):
                    return [f"schema_type_mismatch:{label}"]
                if bool(schema.get("non_empty")) and not value.strip():
                    return [f"schema_non_empty_mismatch:{label}"]
                enum = list(schema.get("enum") or [])
                if enum and value not in enum:
                    return [f"schema_enum_mismatch:{label}"]
                return []
            if schema_type == "boolean":
                return [] if isinstance(value, bool) else [f"schema_type_mismatch:{label}"]
            if schema_type == "number":
                valid = isinstance(value, (int, float)) and not isinstance(value, bool)
                return [] if valid else [f"schema_type_mismatch:{label}"]
            if schema_type == "object":
                return [] if isinstance(value, dict) else [f"schema_type_mismatch:{label}"]
            if schema_type == "list":
                if not isinstance(value, list):
                    return [f"schema_type_mismatch:{label}"]
                violations: list[str] = []
                required_count = schema.get("required_count")
                if isinstance(required_count, int) and len(value) != required_count:
                    violations.append(f"schema_count_mismatch:{label}")
                item_schema = schema.get("item")
                if item_schema is not None:
                    for index, item in enumerate(value):
                        item_path = f"{path}[{index}]" if path else f"[{index}]"
                        violations.extend(
                            self._shape_violations(
                                item,
                                item_schema,
                                path=item_path,
                            )
                        )
                return violations
            return []

        if not isinstance(value, dict):
            return [f"schema_type_mismatch:{label}"]
        violations: list[str] = []
        for key, nested_schema in schema.items():
            nested_path = f"{path}.{key}" if path else str(key)
            if key not in value:
                violations.append(f"missing_required_field:{nested_path}")
                continue
            violations.extend(
                self._shape_violations(
                    value[key],
                    nested_schema,
                    path=nested_path,
                )
            )
        return violations
