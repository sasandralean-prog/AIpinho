from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService


def test_patch_planning_contract_blocks_negated_required_evidence():
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/phase4_patch_plan.md",
        content=(
            "## Root Cause\n\n"
            "Root cause not identified with sufficient evidence.\n\n"
            "## Target Files\n\n- src/app.py\n\n"
            "## Target Functions\n\n- not established\n\n"
            "## Strategy\n\nStrategy not available until a supported root cause exists.\n\n"
            "## Rollback\n\nRollback not available until concrete changes are identified.\n\n"
            "## Alternatives\n\nAlternatives not available until a supported root cause exists.\n\n"
            "## Validation\n\nValidation must remain blocked.\n\n"
            "## Risk\n\nRisk is high.\n"
        ),
    )

    assert result.status == "blocked"
    assert "root_cause" in result.missing_requirements
    assert "strategy" in result.missing_requirements
    assert "rollback" in result.missing_requirements
    assert "target_functions" in result.missing_requirements
    assert "alternatives" in result.missing_requirements


def test_patch_planning_contract_accepts_supported_required_evidence():
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/phase4_patch_plan.md",
        content=(
            "## Root Cause\n\n"
            "Causa raiz suportada por evidencias em decoder e player.\n\n"
            "## Target Files\n\n- src/audio/Decoder.kt\n\n"
            "## Target Functions\n\n- decode\n\n"
            "## Strategy\n\nEstrategia: aplicar correcao minima.\n\n"
            "## Rollback\n\nRollback: reverter os hunks aplicados.\n\n"
            "## Alternatives\n\nAlternativas: bloquear formato sem suporte ou ajustar decoder.\n\n"
            "## Validation\n\nValidation: executar testes focados.\n\n"
            "## Risk\n\nRisco: regressao em formatos suportados.\n"
        ),
    )

    assert result.status == "passed"


def test_patch_preview_contract_blocks_deferred_diff_language():
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/patch_preview.md",
        content=(
            "## Target Files\n\n- src/audio/Decoder.kt\n\n"
            "## Concrete Change Preview\n\n"
            "Diff: generated only by the patch execution runtime after approval.\n\n"
            "Before: current implementation remains unchanged.\n\n"
            "After: replacement will be generated later.\n\n"
            "## Validation\n\nValidation: executar testes focados.\n\n"
            "## Rollback\n\nRollback: reverter hunks.\n"
        ),
    )

    assert result.status == "blocked"
    assert "PROPOSAL_CONCRETE_CHANGE_MISSING" in result.missing_requirements
    assert "PROPOSAL_IMPACT_MISSING" in result.missing_requirements
    assert "PROPOSAL_RISK_MISSING" in result.missing_requirements


def test_patch_preview_contract_accepts_structured_repair_proposal_preview():
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/patch_preview.md",
        content=(
            "## Repair Proposal\n\n"
            "- proposal_id: repair_proposal_1\n"
            "- intent: stabilize decoder eof handling\n"
            "- target_file: src/audio/Decoder.kt\n"
            "- target_symbol: decode\n"
            "- symbol_kind: method\n"
            "\n## Target Files\n\n- src/audio/Decoder.kt\n\n"
            "## Concrete Change Preview\n\n"
            "- objective: prevent invalid buffer access on truncated input\n"
            "- current_behavior: decode reads beyond the available bytes on truncated input\n"
            "- expected_behavior: decode validates available bytes before reading the frame header\n"
            "- modification_strategy: add a focused boundary check before the frame read path\n"
            "\n### Affected Symbols\n\n- decode\n\n"
            "### Reasoning\n\n"
            "The selected branch already owns the frame preconditions and can reject truncated input consistently.\n\n"
            "## Impact\n\n"
            "- scope: focused_edit_unit\n"
            "- runtime_behavior: truncated inputs fail consistently without invalid reads\n"
            "- compatibility: preserve public decoder contract and existing success path\n"
            "- risk_level: medium\n"
            "\n### Affected Modules\n\n- src/audio\n\n"
            "## Risks\n\n"
            "- confidence: medium\n"
            "- technical:\n"
            "  - A nearby caller may rely on the previous unchecked path.\n"
            "- behavioral:\n"
            "  - Invalid inputs now fail earlier in the decoder pipeline.\n"
            "- regression:\n"
            "  - Truncated samples must be rechecked against known-good files.\n\n"
            "## Validation\n\nValidation: executar testes focados.\n\n"
            "## Rollback\n\n"
            "- strategy: revert the focused guard and restore the previous branch behavior\n"
            "\n### Rollback Affected Symbols\n\n- decode\n\n"
            "### Rollback Side Effects\n\n- truncated inputs may return to the previous unsafe path\n"
        ),
    )

    assert result.status == "passed"


def test_contract_negation_does_not_contaminate_next_section():
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/phase4_patch_plan.md",
        content=(
            "## Root Cause\n\n"
            "Causa raiz suportada por evidencias em decoder e player.\n\n"
            "## Target Files\n\n- src/audio/Decoder.kt\n\n"
            "## Target Functions\n\n- not established\n\n"
            "## Strategy\n\nEstrategia: aplicar correcao minima.\n\n"
            "## Rollback\n\nRollback: reverter os hunks aplicados.\n\n"
            "## Alternatives\n\nAlternativas: bloquear formato sem suporte ou ajustar decoder.\n\n"
            "## Validation\n\nValidation: executar testes focados.\n\n"
            "## Risk\n\nRisco: regressao em formatos suportados.\n"
        ),
    )

    assert "strategy" not in result.missing_requirements
    assert "target_functions" in result.missing_requirements


def test_semantic_profile_blocks_material_kind_mismatch_without_domain_rules():
    service = ArtifactSemanticContractService()

    result = service.validate(
        logical_path="reports/evidence_bundle.zip",
        content="# Not an archive\n\nThis is text content.",
        content_type="application/zip",
    )

    assert result.status == "blocked"
    assert result.profile is not None
    assert result.profile.expected_kind == "evidence_archive"
    assert result.profile.material_status == "blocked"
    assert "artifact_material_kind_mismatch" in result.missing_requirements


def test_contract_compiler_derives_tabular_schema_from_generic_for_each_prompt():
    service = ArtifactSemanticContractService()
    declared = service.compile_contract_from_prompt(
        logical_path="reports/discovered_entities.csv",
        content_type="text/csv",
        prompt=(
            "Para cada entidade registrar:\n\n"
            "nome\n"
            "extensao\n"
            "tamanho\n\n"
            "Artifacts obrigatorios\n\n"
            "reports/discovered_entities.csv\n"
        ),
    )

    result = service.validate(
        logical_path="reports/discovered_entities.csv",
        content_type="text/csv",
        declared_contract=declared,
        content="nome,extensao\nexample,txt\n",
    )

    assert result.status == "blocked"
    assert result.profile is not None
    assert result.profile.expected_schema == ["nome", "extensao", "tamanho"]
    assert "artifact_schema_field_missing:tamanho" in result.missing_requirements


def test_semantic_profile_accepts_structurally_and_semantically_complete_collection():
    service = ArtifactSemanticContractService()
    declared = service.compile_contract_from_prompt(
        logical_path="reports/discovered_entities.csv",
        content_type="text/csv",
        prompt=(
            "For each discovered entity record:\n\n"
            "name\n"
            "extension\n"
            "size\n\n"
            "Required artifacts\n\n"
            "reports/discovered_entities.csv\n"
        ),
    )

    result = service.validate(
        logical_path="reports/discovered_entities.csv",
        content_type="text/csv",
        declared_contract=declared,
        content="name,extension,size\nexample,txt,12\n",
    )

    assert result.status == "passed"
    assert result.profile is not None
    assert result.profile.completeness_score == 1.0
    assert result.profile.semantic_status == "passed"


def test_consistency_gap_detects_conflicting_claims_between_artifacts():
    service = ArtifactSemanticContractService()
    first = service.profile(
        logical_path="reports/a.json",
        content_type="application/json",
        content_bytes=b'{"status": "ok"}',
    )
    second = service.profile(
        logical_path="reports/b.csv",
        content_type="text/csv",
        content_bytes=b"name\nvalue\n",
    )
    first.observed_semantics["claims"] = {"entity_count": 1}
    second.observed_semantics["claims"] = {"entity_count": 2}

    compared = service.compare_profiles([first, second])

    assert compared[1].consistency_status == "blocked"
    assert compared[1].consistency_gaps[0].gap_type == "artifact_consistency_gap"


def test_semantic_contract_blocks_runtime_entity_gaps_from_renderer():
    service = ArtifactSemanticContractService()
    declared = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["name", "extension", "codec"],
        "expected_semantics": {"collection_items_required": True},
        "runtime_semantic_gaps": [
            {
                "gap_type": "ATTRIBUTE_NOT_OBSERVED:codec",
                "severity": "high",
                "expected": "codec",
                "observed": "missing",
                "repair_hint": "Collect the declared attribute before semantic completion.",
            }
        ],
        "schema_coverage": {"status": "partial", "missing_fields": ["codec"]},
    }

    result = service.validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        declared_contract=declared,
        content="name,extension,codec\nalpha.txt,txt,\n",
    )

    assert result.status == "blocked"
    assert "ATTRIBUTE_NOT_OBSERVED:codec" in result.missing_requirements
    assert result.profile is not None
    assert result.profile.schema_coverage["status"] == "partial"


def test_semantic_contract_uses_bound_attribute_observations_for_runtime_gaps():
    service = ArtifactSemanticContractService()
    declared = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["nome", "codec", "observações"],
        "canonical_schema": ["name", "codec", "observations"],
        "attribute_contracts": [
            {"canonical_key": "name", "display_label": "nome", "raw_label": "nome"},
            {"canonical_key": "codec", "display_label": "codec", "raw_label": "codec"},
            {"canonical_key": "observations", "display_label": "observações", "raw_label": "observações"},
        ],
        "artifact_observation_binding": {
            "status": "bound",
            "bound_counts_by_canonical_key": {"codec": 1},
            "bound_observed_canonical_keys": ["codec"],
            "bound_observations": [
                {
                    "observation_id": "attribute_observation_codec",
                    "entity_id": "file_1",
                    "canonical_key": "codec",
                    "attribute_name": "codec",
                    "evidence_refs": ["evidence_codec"],
                    "capability_id": "media_metadata_reader",
                    "observer_id": "media_metadata_observer",
                    "confidence": 0.96,
                }
            ],
        },
        "runtime_semantic_gaps": [
            {"gap_type": "ATTRIBUTE_NOT_OBSERVED:codec", "severity": "high", "expected": "codec"},
            {"gap_type": "ATTRIBUTE_NOT_OBSERVED:observations", "severity": "high", "expected": "observations"},
        ],
    }

    result = service.validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        declared_contract=declared,
        content="nome,codec,observações\nalpha,aac,\n",
    )

    assert result.status == "blocked"
    assert "ATTRIBUTE_NOT_OBSERVED:codec" not in result.missing_requirements
    assert "ATTRIBUTE_NOT_OBSERVED:observations" in result.missing_requirements
    assert result.profile is not None
    assert result.profile.bound_attribute_observations[0]["canonical_key"] == "codec"
    assert result.profile.evidence_summary["bound_attribute_observation_count"] == 1


def test_semantic_contract_preserves_observational_coverage_report():
    service = ArtifactSemanticContractService()
    declared = {
        "expected_kind": "tabular_collection",
        "artifact_logical_path": "reports/entities.csv",
        "artifact_kind": "tabular_collection",
        "task_run_id": "task_run_semantic",
        "expected_schema": ["name", "generic_signal"],
        "canonical_schema": ["name", "generic_signal"],
        "attribute_contracts": [
            {
                "canonical_key": "name",
                "display_label": "name",
                "raw_label": "name",
                "requiredness": "required",
            }
        ],
        "runtime_semantic_gaps": [
            {
                "gap_type": "ATTRIBUTE_NOT_OBSERVED:generic_signal",
                "reason_code": "NO_MATCHING_CAPABILITY",
                "severity": "high",
                "expected": "generic_signal",
                "observed": "missing",
            }
        ],
        "schema_coverage": {
            "status": "partial",
            "semantic_coverage_report": {
                "attribute_coverage": 0.5,
                "capability_coverage": 0.5,
                "evidence_coverage": 0.5,
                "missing_capabilities": ["generic_signal"],
                "blocking_reasons": ["NO_MATCHING_CAPABILITY"],
                "is_semantically_complete": False,
            },
        },
    }

    result = service.validate(
        logical_path="reports/entities.csv",
        content_type="text/csv",
        declared_contract=declared,
        content="name,generic_signal\nalpha,\n",
    )

    assert result.status == "blocked"
    assert result.profile is not None
    assert result.profile.artifact_logical_path == "reports/entities.csv"
    assert result.profile.artifact_kind == "tabular_collection"
    assert result.profile.task_run_id == "task_run_semantic"
    assert result.profile.canonical_schema == ["name", "generic_signal"]
    assert result.profile.attribute_contracts[0]["canonical_key"] == "name"
    report = result.profile.schema_coverage["semantic_coverage_report"]
    assert report["missing_capabilities"] == ["generic_signal"]
    assert report["is_semantically_complete"] is False
