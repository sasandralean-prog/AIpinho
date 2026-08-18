from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import (
    UniversalArtifactRegistryService,
)
from aipinho.services.governance.lifecycle.canonical_public_chat_service import (
    CanonicalPublicChatService,
)
from aipinho.services.governance.lifecycle.governance_lifecycle_service import (
    GovernanceLifecycleService,
)
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _fixture_root() -> Path:
    root = PATHS.project_root / "data" / "tmp_runtime_vertical_slice_tests" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def _workspace(root: Path) -> Path:
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "package.json").write_text('{"scripts":{"test":"echo ok"}}\n', encoding="utf-8")
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "src" / "main.js").write_text("console.log('ok')\n", encoding="utf-8")
    return workspace


def _chat(root: Path) -> tuple[CanonicalPublicChatService, ReadonlyAnalysisArtifactRuntimeService]:
    runtime = TaskRuntimeService(store=TaskRunStore(root / "task_runs"))
    artifacts = UniversalArtifactRegistryService(
        registry=ArtifactRegistryRepository(root / "artifact_registry.json"),
        store_root=root / "artifacts",
    )
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        artifacts=artifacts,
        phase_store_path=root / "phase_store.json",
    )
    return CanonicalPublicChatService(readonly_artifact_runtime=service), service


def _hash_tree(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for item in sorted(path.rglob("*")):
        if item.is_file():
            hashes[str(item.relative_to(path))] = hashlib.sha256(item.read_bytes()).hexdigest()
    return hashes


def test_readonly_analysis_artifacts_create_taskrun_without_workspace_mutation() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    before = _hash_tree(workspace)
    chat, service = _chat(root)

    response = chat.respond(
        ChatRequest(
            session_id="chat_vertical_slice",
            message=(
                f'Fase 1. Analise os arquivos em "{workspace}" read-only e gere artifacts '
                "reports/phase1_summary.md e reports/phase1_inventory.json. Nao escreva no workspace."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    task_run_id = str(response.result_ref_id)
    assert response.task_id and response.task_id.startswith("task_")
    assert task_run_id.startswith("task_run_")
    assert response.approval_id is None
    assert len(response.artifact_links) == 2
    assert _hash_tree(workspace) == before
    assert response.governance_lifecycle["completion"]["safe_to_report_success"] is True
    assert response.governance_lifecycle["speaker_truth"]["can_claim_success"] is True

    run = service.runtime.store.get_run(task_run_id)
    result = service.runtime.store.get_result(task_run_id)
    assert run is not None and run.status == "completed"
    assert run.task_id == response.task_id
    assert run.contract_type == "analysis_readonly"
    assert run.runtime_profile == "readonly_analysis"
    assert run.requested_actions == ["read_files"]
    assert run.policy_snapshot["approval_required_for"] == []
    assert run.intent_map["workspace_mutation"] is False
    assert run.intent_map["artifact_generation"] is True
    assert result is not None and result.status == "completed"
    assert result.outputs["validation_result"]["status"] == "passed"
    assert response.governance_lifecycle["validation"]["status"] == "passed"
    assert run.canonical_state is not None
    assert run.canonical_state.status == "COMPLETED"
    assert run.canonical_state.safe_to_report_success is True
    assert run.required_artifacts == ["reports/phase1_summary.md", "reports/phase1_inventory.json"]
    assert run.missing_artifacts == []
    assert len(run.produced_artifacts) == 2
    for link in response.artifact_links:
        record = service.artifacts.get(link.artifact_id)
        assert record is not None
        assert record["status"] == "ready"
        assert record["artifact_id"]
        assert record["storage_ref"]
        assert record["task_run_id"] == run.run_id
        assert record["logical_path"] in run.required_artifacts
        assert any(item["artifact_id"] == record["artifact_id"] for item in run.produced_artifacts)
        assert not str(record["local_path"]).startswith(str(workspace))


def test_h1_analysis_readonly_contract_does_not_promote_to_filesystem_write() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Execute discovery e analysis read-only do workspace. "
            "Gere artifacts reports/firetest5/phase1_discovery.md e reports/firetest5/project_inventory.md. "
            "Nao alterar codigo, nao modificar o projeto e nao escrever no workspace."
        ),
        source_channel="unit",
        operation_type="workspace_analysis_readonly",
        expected_outputs=[
            "project_analysis_report",
            "artifact_result",
            "validation_result",
            "artifact:reports/firetest5/phase1_discovery.md",
        ],
        executable_plan_ref="readonly_analysis_artifact_plan",
    )

    assert snapshot.operation_contract.contract_type == "analysis_readonly"
    assert snapshot.operation_contract.runtime_profile == "readonly_analysis"
    assert snapshot.operation_contract.requested_actions == []
    assert snapshot.policy.requires_approval is False
    assert snapshot.approval_gate.required is False
    assert snapshot.execution_plan.executable is True
    assert snapshot.execution_plan.executable_plan_ref == "readonly_analysis_artifact_plan"


def test_h3_complete_readonly_artifact_prompt_bootstraps_without_clarification() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    chat, service = _chat(root)

    response = chat.respond(
        ChatRequest(
            session_id="chat_h3_bootstrap",
            message=(
                f'Fase 1. Faca discovery, audit e inventory em "{workspace}" read-only. '
                "Gere artifacts reports/firetest5/phase1_discovery.md, "
                "reports/firetest5/project_inventory.md e reports/firetest5/music_inventory.csv. "
                "Nao alterar codigo. Nao modificar workspace. Nao escrever no projeto."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.task_id is not None
    assert response.operation_type == "workspace_analysis_readonly"
    assert response.approval_id is None
    assert "needs_clarification" not in str(response.model_dump(mode="json")).casefold()
    bootstrap = response.governance_lifecycle["pre_task_bootstrap"]
    assert bootstrap["status"] == "complete"
    assert [item["stage"] for item in bootstrap["stages"]] == [
        "ChatIngressReceived",
        "PromptNormalized",
        "PreviewStarted",
        "IntentResolutionStarted",
        "IntentResolutionFinished",
        "OperationContractSelected",
        "TaskBootstrapStarted",
        "TaskBootstrapFinished",
        "TaskCreated",
        "TaskRunCreated",
    ]
    run = service.runtime.store.get_run(str(response.result_ref_id))
    assert run is not None
    assert run.task_id == response.task_id
    assert run.contract_type == "analysis_readonly"
    assert run.workspace == str(workspace)


def test_readonly_artifact_discovery_with_no_workspace_mutation_language_keeps_all_roots() -> None:
    root = _fixture_root()
    project = root / "project root"
    library = root / "library root"
    project.mkdir(parents=True)
    library.mkdir(parents=True)
    (project / "package.json").write_text('{"scripts":{"test":"echo ok"}}\n', encoding="utf-8")
    (project / "src").mkdir()
    (project / "src" / "main.js").write_text("console.log('ok')\n", encoding="utf-8")
    (library / "song.m4a").write_bytes(b"fake media")
    before = _hash_tree(project)
    chat, service = _chat(root)

    response = chat.respond(
        ChatRequest(
            session_id="chat_readonly_discovery_with_multiple_roots",
            message=(
                "Execute descoberta governada completa.\n"
                f"Projeto\n\"{project}\"\n"
                f"Biblioteca\n\"{library}\"\n"
                "Esta execucao NAO pode modificar nenhum arquivo do projeto.\n"
                "Mapear stack, scanner, metadata e inventario.\n"
                "Artifacts obrigatorios reports/discovery/summary.md, reports/discovery/inventory.csv "
                "e reports/discovery/evidence.zip.\n"
                "Sem modificar o workspace."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.status == "ok"
    assert response.operation_type == "workspace_analysis_readonly"
    assert response.task_id is not None
    assert response.approval_id is None
    assert len(response.artifact_links) == 3
    assert _hash_tree(project) == before
    run = service.runtime.store.get_run(str(response.result_ref_id))
    assert run is not None
    assert run.workspace == str(project)
    assert run.intent_map["workspace_mutation"] is False
    assert str(library) not in run.intent_map["external_roots"]
    assert str(library) in run.intent_map["library_roots"]
    assert run.intent_map["readonly_flags"][str(project)] is True
    assert run.intent_map["readonly_flags"][str(library)] is True
    assert "reports/discovery/evidence.zip" in run.required_artifacts


def test_public_chat_and_service_path_apply_corpus_entity_selection_policy() -> None:
    root = _fixture_root()
    project = root / "project_app"
    library = root / "library_corpus"
    (project / "src").mkdir(parents=True)
    (project / "build").mkdir()
    (project / ".gradle").mkdir()
    library.mkdir(parents=True)
    (project / "src" / "Main.kt").write_text("fun main() {}", encoding="utf-8")
    (project / "build" / "Generated.class").write_bytes(b"class")
    (project / ".gradle" / "cache.lock").write_text("lock", encoding="utf-8")
    (project / "build.gradle.kts").write_text("plugins {}", encoding="utf-8")
    (library / "Alpha.track").write_text("content", encoding="utf-8")
    (library / "Beta.track").write_text("content", encoding="utf-8")
    chat, service = _chat(root)
    message = (
        "Fase 1. Execute descoberta governada readonly.\n"
        f"Projeto\n\"{project}\"\n"
        f"Biblioteca\n\"{library}\"\n"
        "Campos:\n"
        "- nome\n"
        "- extensão\n"
        "- tamanho\n"
        "- codec\n"
        "Artifacts obrigatorios reports/firetest5/music_inventory.csv.\n"
        "Nao modificar workspace."
    )
    request = ChatRequest(
        session_id="chat_h1b2_runtime_propagation",
        message=message,
        context=ChatContext(surface="api"),
    )

    service_context = service._request_workspace_context(request)
    graph = service.observed_entities.compile(
        workspace=str(project),
        workspace_context=service_context,
    ).model_dump(mode="json")
    service_perception = service.perception.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "artifact_logical_path": "reports/firetest5/music_inventory.csv",
            "expected_schema": ["nome", "extensão", "tamanho", "codec"],
            "workspace_context": service_context,
        },
    )
    service_selected = {
        item["entity_id"]: item
        for item in graph["entities"]
        if item["entity_id"] in set(service_perception.candidate_entity_set.selected_entity_ids)
    }
    assert service_context["project_root"] == str(project)
    assert str(library) in service_context["library_roots"]
    assert graph["roots_scanned_by_role"]["project_root"] == [str(project.resolve())]
    assert graph["roots_scanned_by_role"]["library_root"] == [str(library.resolve())]
    assert service_selected
    assert {item["source_root_role"] for item in service_selected.values()} == {"library_root"}
    assert all(item["entity_role"] == "corpus_file" for item in service_selected.values())

    response = chat.respond(request, source_channel="api_chat")

    assert response.status == "blocked"
    assert response.task_id is not None
    assert response.approval_id is None
    run_id = str(response.result_ref_id)
    run = service.runtime.store.get_run(run_id)
    result = service.runtime.store.get_result(run_id)
    assert run is not None and result is not None
    assert result.status == "blocked"
    assert result.completion.safe_to_report_success is False
    record = next(
        item
        for item in (service.artifacts.get(link.artifact_id) for link in response.artifact_links)
        if item and item.get("logical_path") == "reports/firetest5/music_inventory.csv"
    )
    assert record is not None
    rows = list(csv.DictReader(Path(record["local_path"]).read_text(encoding="utf-8").splitlines()))
    names = {row["nome"] for row in rows}
    assert names == {"Alpha.track", "Beta.track"}
    assert {row["extensão"] for row in rows} == {"track"}
    assert "Generated.class" not in names
    assert "build.gradle.kts" not in names
    declared_contract = record["metadata"]["declared_contract"]
    entity_summary = declared_contract["observed_entity_summary"]
    perception = entity_summary["perception"]
    assert entity_summary["roots_scanned_by_role"]["library_root"] == [str(library.resolve())]
    assert entity_summary["entities_selected_by_artifact"]["reports/firetest5/music_inventory.csv"] == 2
    assert entity_summary["entities_rejected_by_policy"]
    assert entity_summary["selection_counts"]["selected_count"] < entity_summary["selection_counts"]["candidate_count"]
    selected_entities = entity_summary["entities"]
    assert {item["source_root_role"] for item in selected_entities} == {"library_root"}
    assert {item["entity_role"] for item in selected_entities} == {"corpus_file"}
    match_statuses = {
        item["match_status"]
        for item in perception["observation_plan"]["capability_matches"]
        if item.get("canonical_key") == "codec"
    }
    assert "NO_MATCHING_CAPABILITY" in match_statuses
    report = perception["semantic_coverage_report"]
    assert "codec" in report["missing_capabilities"]
    assert "codec" in report["missing_attributes"]
    summary = UniversalTaskSessionService(
        store=service.runtime.store,
        approvals=chat.approval_service,
        artifacts=service.artifacts,
    ).summary(run_id)
    assert summary is not None
    assert summary["status"] == "BLOCKED"
    assert summary["approval"]["status"] == "not_required"
    assert summary["observational_cognition"]["entities_selected_by_artifact"]["reports/firetest5/music_inventory.csv"] == 2
    assert response.governance_lifecycle["speaker_truth"]["can_claim_success"] is False


def test_phase_two_blocks_when_required_previous_phase_artifacts_are_missing() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    chat, _service = _chat(root)

    response = chat.respond(
        ChatRequest(
            session_id="chat_missing_phase",
            message=(
                f'Fase 2. Use os artifacts da Fase 1 e analise "{workspace}" read-only; '
                "gere artifacts reports/phase2_summary.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert response.status == "blocked"
    assert response.task_id is None
    assert response.contract_preview["phase_dependency_result"]["status"] == "blocked"
    assert response.governance_lifecycle["speaker_truth"]["can_claim_success"] is False


def test_phase_two_consumes_real_phase_one_artifacts() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    chat, service = _chat(root)
    session_id = "chat_phase_chain"

    phase_one = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                f'Fase 1. Analise os arquivos em "{workspace}" read-only e gere artifacts '
                "reports/phase1_summary.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_two = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                f'Fase 2. Use os artifacts da Fase 1 e analise novamente "{workspace}" read-only; '
                "gere artifacts reports/phase2_summary.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert phase_one.status == "ok"
    assert phase_two.status == "ok"
    assert phase_one.artifact_links
    assert phase_two.artifact_links
    dependency = phase_two.contract_preview["phase_dependency_result"]
    assert dependency["status"] == "passed"
    assert dependency["artifacts"][0]["artifact_id"] == phase_one.artifact_links[0].artifact_id
    assert service.runtime.store.get_result(str(phase_two.result_ref_id)).completion.safe_to_report_success is True


def test_dependent_readonly_phase_inherits_workspace_and_negative_build_is_not_shell() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    chat, service = _chat(root)
    session_id = "chat_phase_chain_without_repeated_workspace"

    phase_one = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                f'Fase 1. Analise os arquivos em "{workspace}" read-only e gere artifacts '
                "reports/phase1_summary.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_two = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                "Fase 2. Utilize exclusivamente os artifacts produzidos pela Fase 1. "
                "Nao modificar codigo. Nao executar build. Analise decoder, player e metadata. "
                "Artifacts reports/phase2_static_analysis.md e reports/static_risk_matrix.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert phase_one.status == "ok"
    assert phase_two.status == "ok"
    assert phase_two.operation_type == "workspace_analysis_readonly"
    assert phase_two.actions == []
    assert phase_two.approval_id is None
    assert len(phase_two.artifact_links) == 2
    run = service.runtime.store.get_run(str(phase_two.result_ref_id))
    assert run is not None
    assert run.workspace == str(workspace)
    assert run.operation_type == "workspace_analysis_readonly"
    assert run.requested_actions == ["read_files"]


def test_dependent_analysis_artifact_phase_without_explicit_negative_constraint_is_readonly() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    chat, service = _chat(root)
    session_id = "chat_phase_chain_analysis_outputs"

    phase_one = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                f'Fase 1. Analise os arquivos em "{workspace}" read-only e gere artifacts '
                "reports/phase1_summary.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_two = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                "Fase 2. Utilize os artifacts da Fase 1. Analise decoder e player. "
                "Artifacts reports/phase2_static_analysis.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_three = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                "Fase 3. Utilizar os artifacts das fases anteriores. "
                "Selecionar uma entrada funcional e uma entrada problematica. "
                "Comparar codec, container, bitrate, metadata, logs, excecoes e pipeline. "
                "Responder o que muda, se existe padrao e se a hipotese anterior permanece. "
                "Artifacts reports/phase3_experimental.md, reports/music_comparison.md "
                "e reports/music_diff.csv."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert phase_one.status == "ok"
    assert phase_two.status == "ok"
    assert phase_three.status == "ok"
    assert phase_three.operation_type == "workspace_analysis_readonly"
    assert phase_three.actions == []
    assert phase_three.approval_id is None
    assert len(phase_three.artifact_links) == 3
    dependency = phase_three.contract_preview["phase_dependency_result"]
    assert dependency["status"] == "passed"
    run = service.runtime.store.get_run(str(phase_three.result_ref_id))
    assert run is not None
    assert run.workspace == str(workspace)
    assert run.operation_type == "workspace_analysis_readonly"
    assert run.requested_actions == ["read_files"]
    assert run.required_artifacts == [
        "reports/phase3_experimental.md",
        "reports/music_comparison.md",
        "reports/music_diff.csv",
    ]


def test_planning_artifact_phase_uses_previous_evidence_without_workspace_repeat() -> None:
    root = _fixture_root()
    workspace = _workspace(root)
    chat, service = _chat(root)
    session_id = "chat_phase_chain_previous_evidence"

    phase_one = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                f'Fase 1. Analise os arquivos em "{workspace}" read-only e gere artifacts '
                "reports/phase1_summary.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_two = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                "Fase 2. Utilize os artifacts da Fase 1. Analise decoder e player. "
                "Artifacts reports/phase2_static_analysis.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_three = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                "Fase 3. Utilizar os artifacts das fases anteriores. "
                "Comparar entradas, logs e pipeline. "
                "Artifacts reports/phase3_experimental.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )
    phase_four = chat.respond(
        ChatRequest(
            session_id=session_id,
            message=(
                "Fase 4. Utilizar todas as evid?ncias anteriores. "
                "Ainda nao modificar codigo. Responder causa raiz, arquivos, funcoes, "
                "estrategia, riscos, rollback e alternativas. "
                "Artifacts reports/phase4_patch_plan.md, reports/patch_preview.md "
                "e reports/risk_analysis.md."
            ),
            context=ChatContext(surface="api"),
        ),
        source_channel="api_chat",
    )

    assert phase_one.status == "ok"
    assert phase_two.status == "ok"
    assert phase_three.status == "ok"
    assert phase_four.status == "blocked"
    assert phase_four.operation_type == "workspace_analysis_readonly"
    assert phase_four.task_id is not None
    assert phase_four.approval_id is None
    assert len(phase_four.artifact_links) == 3
    assert phase_four.governance_lifecycle["validation"]["status"] == "blocked"
    assert phase_four.governance_lifecycle["completion"]["safe_to_report_success"] is False
    assert phase_four.governance_lifecycle["speaker_truth"]["can_claim_success"] is False
    run = service.runtime.store.get_run(str(phase_four.result_ref_id))
    assert run is not None
    assert run.workspace == str(workspace)
    assert run.status == "blocked"
    assert run.operation_type == "workspace_analysis_readonly"
    assert run.required_artifacts == [
        "reports/phase4_patch_plan.md",
        "reports/patch_preview.md",
        "reports/risk_analysis.md",
    ]
    result = service.runtime.store.get_result(str(phase_four.result_ref_id))
    assert result is not None
    assert any(
        item.startswith("artifact_semantic_contract:reports/phase4_patch_plan.md")
        for item in result.completion.missing_outcomes
    )


def test_accented_negative_build_constraint_routes_to_readonly_artifact_analysis() -> None:
    decision = GovernanceLifecycleService().intent_resolution.resolve(
        "Fase 2. Não modificar código. Não executar build. "
        "Analisar decoder e player. Artifacts reports/phase2_static_analysis.md.",
        source_channel="unit",
    )

    assert decision.intent_type == "workspace_analysis_readonly"
    assert decision.operation_type == "workspace_analysis_readonly"
    assert decision.readonly is True
    assert decision.side_effect_requested is False


def test_readonly_artifact_lifecycle_outputs_allow_speaker_truth_success() -> None:
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Fase 1. Analise em read-only e gere artifacts reports/phase1_summary.md."
        ),
        source_channel="unit",
        operation_type="workspace_analysis_readonly",
        contract_type="readonly_analysis",
        runtime_profile="readonly_analysis",
        executable_plan_ref="task_run_test",
        expected_outputs=[
            "project_analysis_report",
            "artifact_result",
            "validation_result",
            "artifact:reports/phase1_summary.md",
        ],
        outputs={
            "project_analysis_report": {"status": "present"},
            "artifact_result": {"artifact_ids": ["artifact_test"]},
            "validation_result": {"status": "passed"},
            "artifact:reports/phase1_summary.md": {"artifact_id": "artifact_test"},
        },
        proposed_completion_status="completed",
    )

    assert snapshot.completion.safe_to_report_success is True
    assert snapshot.speaker_truth.can_claim_success is True
    assert snapshot.operation_contract.requested_actions == []
