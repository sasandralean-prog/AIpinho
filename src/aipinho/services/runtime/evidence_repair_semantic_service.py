from __future__ import annotations

from typing import Any


class EvidenceRepairSemanticService:
    """Deterministic projection of bounded evidence-repair semantics.

    This service never grants authority. It only projects whether the exact
    bounded focus paths supplied by canonical mission continuation were
    actually observed well enough to support the next governed phase.
    """

    @staticmethod
    def context(run: Any) -> dict[str, Any]:
        continuation = (
            run.intent_map.get("mission_continuation")
            if isinstance(getattr(run, "intent_map", None), dict)
            and isinstance(run.intent_map.get("mission_continuation"), dict)
            else {}
        )
        value = continuation.get("evidence_repair")
        return dict(value) if isinstance(value, dict) else {}

    @classmethod
    def focus_paths(cls, run: Any) -> list[str]:
        repair = cls.context(run)
        return cls._unique(
            [
                str(item)
                for item in list(repair.get("focus_paths") or [])
                if str(item)
            ]
        )

    @classmethod
    def project_analysis_outcome(
        cls,
        result: Any,
        *,
        repair: dict[str, Any] | None = None,
        nonfatal_omission_reasons: list[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        status = str(getattr(result, "status", "") or "")
        safe_to_continue = bool(getattr(result, "safe_to_continue", False))
        if status == "ok" and safe_to_continue:
            safety: bool | str = True
        elif status in {"partial", "degraded"} and safe_to_continue:
            safety = "true_with_limitations"
        else:
            safety = False

        limitations = [
            *list(getattr(result, "warnings", []) or []),
            *list(getattr(result, "limitations", []) or []),
        ]
        if (
            status in {"partial", "degraded"}
            and "project_analysis_partial" not in limitations
        ):
            limitations.append("project_analysis_partial")
        missing_truth = list(getattr(result, "violations", []) or [])
        use_safety: dict[str, Any] = {
            "safe_for_user_report": safety,
        }
        semantic_properties: dict[str, Any] = {}
        repair_metadata: dict[str, Any] = {}

        repair = dict(repair or {})
        focus_paths = cls._unique(
            [
                str(item)
                for item in list(repair.get("focus_paths") or [])
                if str(item)
            ]
        )
        if repair.get("required") and focus_paths:
            bundle = getattr(result, "file_context", None)
            included = {
                str(getattr(item, "path", "") or "")
                for item in list(getattr(bundle, "items", []) or [])
                if str(getattr(item, "status", "") or "") == "included"
                and not bool(getattr(item, "content_truncated", False))
            }
            nonfatal = {
                str(item).strip().casefold()
                for item in list(nonfatal_omission_reasons or [])
                if str(item).strip()
            }
            skipped_reasons: dict[str, set[str]] = {}
            read_plan = getattr(result, "file_read_plan", None)
            if isinstance(read_plan, dict):
                for item in list(read_plan.get("skipped_files") or []):
                    if not isinstance(item, dict):
                        continue
                    path = str(item.get("path") or "")
                    reason = str(item.get("reason") or "").strip().casefold()
                    if path and reason:
                        skipped_reasons.setdefault(path, set()).add(reason)

            unavailable = [
                path
                for path in focus_paths
                if path not in included
                and skipped_reasons.get(path)
                and skipped_reasons[path].issubset(nonfatal)
            ]
            unresolved = [
                path
                for path in focus_paths
                if path not in included and path not in unavailable
            ]
            repair_complete = bool(
                not unresolved
                and safe_to_continue
                and not missing_truth
            )
            use_safety["safe_for_destructive_action"] = repair_complete
            repair_metadata = {
                "required": True,
                "focus_complete": repair_complete,
                "focus_paths": focus_paths,
                "unresolved_paths": unresolved,
            }
            if unavailable:
                repair_metadata["nonfatal_unavailable_paths"] = unavailable
                limitations.append(
                    "evidence_repair_nonfatal_unavailable_disclosed"
                )
            if unresolved:
                limitations.append("evidence_repair_focus_unresolved")

        return {
            "use_safety": use_safety,
            "semantic_properties": semantic_properties,
            **(
                {"evidence_repair": repair_metadata}
                if repair_metadata
                else {}
            ),
            "limitations": cls._unique(
                [str(item) for item in limitations if str(item)]
            ),
            "missing_truth": cls._unique(
                [str(item) for item in missing_truth if str(item)]
            ),
            "required_disclosures": cls._unique(
                [str(item) for item in limitations if str(item)]
            ),
        }

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
