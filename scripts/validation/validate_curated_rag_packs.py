
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = ROOT / "docs" / "rag_curated"
REPORT_ROOT = ROOT / "reports" / "rag_curated"

EXPECTED = [
    "current_aipinho/governance/001_aipinho_constitution.md",
    "current_aipinho/governance/002_policy_ownership_matrix.md",
    "current_aipinho/governance/003_patch_vs_readonly_invariant.md",
    "current_aipinho/governance/004_speaker_truth_policy.md",
    "current_aipinho/governance/005_event_contract_registry.md",
    "current_aipinho/skills/006_tool_permission_envelope.md",
    "current_aipinho/operations/007_14b_manual_only_model_routing.md",
    "current_aipinho/skills/008_external_connector_safety.md",
    "current_aipinho/governance/009_anti_deterministic_routing.md",
    "current_aipinho/governance/010_intent_routing_failure_patterns.md",
    "current_aipinho/context/011_context_admission_rejection.md",
    "current_aipinho/context/012_rag_citation_and_source_trust.md",
    "current_aipinho/context/013_rag_as_evidence_not_truth.md",
    "current_aipinho/context/014_context_purpose_mapping.md",
    "current_aipinho/context/015_smart_chunk_taxonomy.md",
    "current_aipinho/memory/016_memory_candidate_vs_curated_memory.md",
    "legacy_pinhoabacaxi/lessons/017_legacy_rag_sanitized_namespace.md",
    "legacy_pinhoabacaxi/conflicts/018_legacy_to_current_conflict.md",
    "legacy_pinhoabacaxi/pinhoforge/019_pinhoforge_generalized_reference.md",
    "current_aipinho/regression/020_regression_seed_extraction.md",
    "current_aipinho/ux/021_operational_ux_state.md",
    "current_aipinho/operations/022_realtime_reconnect_and_sync_cursor.md",
    "current_aipinho/ux/023_debugger_filter_taxonomy.md",
    "current_aipinho/ux/024_pipeline_permission_visibility.md",
    "current_aipinho/ux/025_raw_sanitized_copy_policy.md",
    "current_aipinho/operations/026_artifact_transfer_safety.md",
    "current_aipinho/operations/027_connection_profiles.md",
    "current_aipinho/ux/028_mobile_desktop_feature_parity.md",
    "current_aipinho/ux/029_neon_cyberpunk_design_system.md",
    "current_aipinho/regression/030_feedback_to_regression_candidate.md",
]

REQUIRED_FIELDS = [
    "rag_pack_id", "title", "namespace", "source_of_truth", "current_source_of_truth",
    "legacy", "trust_level", "status", "version", "owner", "created_from",
    "allowed_purposes", "blocked_purposes", "requires_current_validation",
    "sensitive", "chunk_types", "tags",
]

SECTIONS = [
    "Canonical Summary", "Why This Matters", "Rules", "Allowed Use", "Blocked Use",
    "Good Examples", "Bad Examples", "Anti-patterns", "Regression Seeds",
    "Context Admission Notes", "Validation Checklist", "Current Validation Notes",
]

LIST_FIELDS = {"created_from", "allowed_purposes", "blocked_purposes", "chunk_types", "tags"}


def parse_value(value: str):
    value = value.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, object], list[str]]:
    errors = []
    if not text.startswith("---\n"):
        return {}, ["missing_frontmatter"]
    end = text.find("\n---", 4)
    if end < 0:
        return {}, ["unterminated_frontmatter"]
    raw = text[4:end].splitlines()
    data: dict[str, object] = {}
    current_key = None
    for line in raw:
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(line[4:].strip())
            continue
        if line.startswith("  ") and current_key:
            nested = data.setdefault(current_key, {})
            if isinstance(nested, dict) and ":" in line:
                key, value = line.strip().split(":", 1)
                nested[key] = parse_value(value)
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if not value:
                data[key] = [] if key in LIST_FIELDS else {}
            else:
                data[key] = parse_value(value)
    return data, errors


def regression_seed_count(text: str) -> int:
    match = re.search(r"## Regression Seeds\n\n(?P<body>.*?)(\n## |\Z)", text, re.S)
    if not match:
        return 0
    return len(re.findall(r"^- ", match.group("body"), re.M))


def validate() -> dict[str, object]:
    missing_files = []
    missing_frontmatter_fields = []
    missing_sections = []
    warnings = []
    packs = []
    namespaces = {"current_aipinho_curated": 0, "legacy_pinhoabacaxi_curated": 0}
    for rel in EXPECTED:
        path = DOC_ROOT / rel
        if not path.exists():
            missing_files.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter, errors = parse_frontmatter(text)
        for err in errors:
            warnings.append({"file": rel, "warning": err})
        for field in REQUIRED_FIELDS:
            if field not in frontmatter:
                missing_frontmatter_fields.append({"file": rel, "field": field})
        for section in SECTIONS:
            if f"## {section}" not in text:
                missing_sections.append({"file": rel, "section": section})
        if "TODO" in text or "Lorem ipsum" in text:
            warnings.append({"file": rel, "warning": "placeholder_text"})
        if regression_seed_count(text) < 3:
            warnings.append({"file": rel, "warning": "too_few_regression_seeds"})
        namespace = str(frontmatter.get("namespace", ""))
        if namespace in namespaces:
            namespaces[namespace] += 1
        legacy = bool(frontmatter.get("legacy"))
        if legacy:
            if frontmatter.get("current_source_of_truth") is not False:
                warnings.append({"file": rel, "warning": "legacy_current_source_of_truth_not_false"})
            if frontmatter.get("requires_current_validation") is not True:
                warnings.append({"file": rel, "warning": "legacy_requires_current_validation_not_true"})
        else:
            if frontmatter.get("source_of_truth") is not True:
                warnings.append({"file": rel, "warning": "current_source_of_truth_not_true"})
        if rel.endswith("019_pinhoforge_generalized_reference.md") and "pinhoforge_policy" not in frontmatter:
            warnings.append({"file": rel, "warning": "missing_pinhoforge_policy"})
        packs.append({
            "file": str(path),
            "rag_pack_id": frontmatter.get("rag_pack_id"),
            "title": frontmatter.get("title"),
            "namespace": frontmatter.get("namespace"),
            "source_of_truth": frontmatter.get("source_of_truth"),
            "current_source_of_truth": frontmatter.get("current_source_of_truth"),
            "legacy": frontmatter.get("legacy"),
            "trust_level": frontmatter.get("trust_level"),
            "status": frontmatter.get("status"),
            "allowed_purposes": frontmatter.get("allowed_purposes", []),
            "blocked_purposes": frontmatter.get("blocked_purposes", []),
            "chunk_types": frontmatter.get("chunk_types", []),
            "tags": frontmatter.get("tags", []),
        })
    status = "passed"
    if missing_files or missing_frontmatter_fields or missing_sections or any(w.get("warning") == "placeholder_text" for w in warnings if isinstance(w, dict)):
        status = "failed"
    elif warnings:
        status = "passed_with_warnings"
    result = {
        "status": status,
        "total_packs_expected": len(EXPECTED),
        "total_packs_found": len(packs),
        "namespaces": namespaces,
        "packs": packs,
        "validation": {
            "missing_files": missing_files,
            "missing_frontmatter_fields": missing_frontmatter_fields,
            "missing_sections": missing_sections,
            "warnings": warnings,
        },
    }
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / "rag_curated_pack_validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["# Curated RAG Pack Validation", "", f"Status: `{status}`", "", f"Found: {len(packs)}/{len(EXPECTED)}", "", "## Warnings"]
    if warnings:
        for item in warnings:
            md.append(f"- `{item}`")
    else:
        md.append("- none")
    (REPORT_ROOT / "rag_curated_pack_validation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, ensure_ascii=False))
