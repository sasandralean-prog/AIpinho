from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> tuple[Path, str]:
    path = ROOT / rel
    return path, path.read_text(encoding="utf-8-sig")


def save(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_lifecycle_schema() -> None:
    path, text = load("src/aipinho/schemas/governance/lifecycle.py")
    old = '''    contract_type: str = "conversation"\n    runtime_profile: str = "conversation"\n    requested_actions: list[str] = Field(default_factory=list)\n'''
    new = '''    contract_type: str = "conversation"\n    runtime_profile: str = "conversation"\n    requires_task: bool = False\n    read_only: bool = False\n    artifact_generation: bool = False\n    workspace_mutation: bool = False\n    requested_actions: list[str] = Field(default_factory=list)\n'''
    text = replace_once(text, old, new, label="lifecycle contract semantic dimensions")
    save(path, text)


def patch_governance_lifecycle() -> None:
    path, text = load("src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py")
    text = replace_once(
        text,
        '''        source_channel: str = "unknown",\n        session_id: str | None = None,\n        requested_actions: list[str] | None = None,\n''',
        '''        source_channel: str = "unknown",\n        session_id: str | None = None,\n        operation_id: str | None = None,\n        requested_actions: list[str] | None = None,\n''',
        label="lifecycle operation id input",
    )
    old_artifact = '''            artifact_outputs_requested = (\n                bool(readonly_expected_outputs)\n                and any(\n                    str(item).startswith("artifact")\n                    or str(item) in {"validation_result", "project_analysis_report"}\n                    for item in readonly_expected_outputs\n                )\n                and not (getattr(intent, "negative_constraints", {}) or {}).get("artifact_forbidden")\n            )\n'''
    new_artifact = '''            semantic_artifact_requested = bool(\n                intent.requires_task\n                and getattr(intent.semantic_intent_graph, "artifact_output", False)\n            )\n            artifact_outputs_requested = (\n                (\n                    bool(readonly_expected_outputs)\n                    and any(\n                        str(item).startswith("artifact")\n                        or str(item) in {"validation_result", "project_analysis_report"}\n                        for item in readonly_expected_outputs\n                    )\n                )\n                or semantic_artifact_requested\n            ) and not (getattr(intent, "negative_constraints", {}) or {}).get("artifact_forbidden")\n'''
    text = replace_once(text, old_artifact, new_artifact, label="readonly artifact intent preservation")
    text = replace_once(
        text,
        '''                expected_outputs = readonly_expected_outputs\n''',
        '''                expected_outputs = readonly_expected_outputs or None\n''',
        label="readonly default expected outputs",
    )
    old_contract = '''        contract = CanonicalOperationContract(\n            operation_id=f"op_{uuid4().hex}",\n            session_id=session_id,\n            source_channel=source_channel,\n            intent_type=intent.intent_type,\n            operation_type=op_type,\n            contract_type=contract_type or self._default_contract_type(op_type, actions),\n            runtime_profile=runtime_profile or self._default_runtime_profile(op_type, actions),\n            requested_actions=actions,\n            target_paths=list(dict.fromkeys(target_paths or [])),\n            workspace_path=workspace_path,\n            risk_level="medium" if actions else "low",\n            trace=[{"stage": "canonical_contract", "source": "GovernanceLifecycleService"}],\n        )\n'''
    new_contract = '''        semantic_artifact_requested = bool(\n            getattr(intent.semantic_intent_graph, "artifact_output", False)\n        )\n        contract_artifact_generation = bool(\n            semantic_artifact_requested\n            or any(\n                str(item).startswith("artifact")\n                or str(item) in {"artifact_result", "project_analysis_report"}\n                for item in (expected_outputs or [])\n            )\n        )\n        contract_requires_task = bool(intent.requires_task or contract_artifact_generation)\n        contract_read_only = bool(intent.readonly)\n        contract_workspace_mutation = bool(\n            not contract_read_only\n            and set(actions).intersection(self.side_effect_actions)\n        )\n        contract = CanonicalOperationContract(\n            operation_id=operation_id or f"op_{uuid4().hex}",\n            session_id=session_id,\n            source_channel=source_channel,\n            intent_type=intent.intent_type,\n            operation_type=op_type,\n            contract_type=contract_type or self._default_contract_type(op_type, actions),\n            runtime_profile=runtime_profile or self._default_runtime_profile(op_type, actions),\n            requires_task=contract_requires_task,\n            read_only=contract_read_only,\n            artifact_generation=contract_artifact_generation,\n            workspace_mutation=contract_workspace_mutation,\n            requested_actions=actions,\n            target_paths=list(dict.fromkeys(target_paths or [])),\n            workspace_path=workspace_path,\n            risk_level="medium" if actions else "low",\n            trace=[{"stage": "canonical_contract", "source": "GovernanceLifecycleService"}],\n        )\n'''
    text = replace_once(text, old_contract, new_contract, label="canonical contract semantic dimensions")
    save(path, text)


def patch_policy() -> None:
    path, text = load("src/aipinho/services/governance/policy/canonical_policy_service.py")
    old = '''        if contract.operation_type in {\n            "conversation",\n            "product_planning_readonly",\n            "workspace_permission_list",\n            "session_diagnostic",\n            "workspace_analysis_readonly",\n            "readonly_analysis",\n            "workspace_fix_request",\n            "capability_truth",\n        }:\n'''
    new = '''        governed_readonly_execution = bool(\n            contract.read_only\n            and contract.requires_task\n            and contract.artifact_generation\n            and not contract.workspace_mutation\n        )\n        if not governed_readonly_execution and contract.operation_type in {\n            "conversation",\n            "product_planning_readonly",\n            "workspace_permission_list",\n            "session_diagnostic",\n            "workspace_analysis_readonly",\n            "readonly_analysis",\n            "workspace_fix_request",\n            "capability_truth",\n        }:\n'''
    text = replace_once(text, old, new, label="policy readonly execution distinction")
    save(path, text)


def patch_canonical_runtime() -> None:
    path, text = load("src/aipinho/services/governance/runtime/canonical_runtime_service.py")
    old = '''        readonly_artifact_execution = (\n            bool(executable_plan_ref)\n            and contract.runtime_profile == "readonly_analysis"\n            and "artifact_result" in outputs\n        )\n        needs_execution_plan = (\n'''
    new = '''        readonly_artifact_execution = bool(\n            contract.read_only\n            and contract.requires_task\n            and contract.artifact_generation\n            and not contract.workspace_mutation\n        )\n        effective_executable_plan_ref = executable_plan_ref or (\n            f"readonly_analysis:{contract.operation_id}"\n            if readonly_artifact_execution\n            else None\n        )\n        needs_execution_plan = (\n'''
    text = replace_once(text, old, new, label="runtime readonly execution semantics")
    text = replace_once(
        text,
        '''        if executable_plan_ref:\n            return CanonicalExecutionPlan(\n                preview_kind=PreviewKind.EXECUTABLE,\n                executable=True,\n                executable_plan_ref=executable_plan_ref,\n''',
        '''        if effective_executable_plan_ref:\n            return CanonicalExecutionPlan(\n                preview_kind=PreviewKind.EXECUTABLE,\n                executable=True,\n                executable_plan_ref=effective_executable_plan_ref,\n''',
        label="runtime executable plan ref",
    )
    save(path, text)


def patch_public_route_lifecycle() -> None:
    path, text = load("src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py")
    text = replace_once(
        text,
        '''            source_channel=source_channel,\n            session_id=response.session_id,\n            requested_actions=actions,\n''',
        '''            source_channel=source_channel,\n            session_id=response.session_id,\n            operation_id=response.operation_id,\n            requested_actions=actions,\n''',
        label="public finalization operation continuity",
    )
    save(path, text)


def patch_public_chat() -> None:
    path, text = load("src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py")
    text = replace_once(
        text,
        '''                execution = self.readonly_artifact_runtime.start_public_boundary(\n                    request=request,\n                    workspace=workspace,\n                    label="WORKSPACE_ANALYSIS_ARTIFACTS_READY",\n                )\n''',
        '''                execution = self.readonly_artifact_runtime.start_public_boundary(\n                    request=request,\n                    workspace=workspace,\n                    label="WORKSPACE_ANALYSIS_ARTIFACTS_READY",\n                    operation_id=snapshot.operation_contract.operation_id,\n                )\n''',
        label="chat to runtime operation continuity",
    )
    save(path, text)


def patch_task_runtime() -> None:
    path, text = load("src/aipinho/services/runtime/task_runtime_service.py")
    text = replace_once(
        text,
        '''from aipinho.schemas.runtime.task_run_request import TaskRunRequest\n''',
        '''from aipinho.schemas.runtime.task_run_request import TaskRunRequest\nfrom aipinho.schemas.runtime.task_run_plan import TaskRunPlan\n''',
        label="task runtime plan import",
    )
    marker = '''    def create_run(self, request: TaskRunRequest) -> TaskRun:\n'''
    if text.count(marker) != 1:
        raise RuntimeError(f"task runtime create_run anchor count={text.count(marker)}")
    reserve_method = '''    def reserve_run(self, request: TaskRunRequest) -> TaskRun:\n        """Persist canonical runtime identity before expensive planning/enrichment.\n\n        A reservation is a real TaskRun in created state, not a placeholder for a\n        second run. `create_run` may enrich only this same identity when the\n        request carries the reserved task/task-run/operation ids.\n        """\n        effective_operation_type = str(\n            request.operation_type\n            or request.intent_map.get("operation_type")\n            or request.intent_map.get("intent_type")\n            or request.contract_type\n        )\n        bootstrap = self.bootstrap.bootstrap(\n            TaskBootstrapRequest(\n                session_id=request.session_id,\n                workspace=request.workspace,\n                contract_type=request.contract_type,\n                operation_type=effective_operation_type,\n                runtime_profile=request.runtime_profile,\n                requested_actions=list(request.requested_actions),\n                intent_map=dict(request.intent_map),\n                source_channel=request.source_channel,\n                task_id=request.task_id,\n                operation_id=request.operation_id,\n                task_run_id=request.task_run_id,\n                workspace_id=request.workspace_id,\n                project_id=request.project_id,\n                parent_task_id=request.parent_task_id,\n            )\n        )\n        task = bootstrap.universal_task\n        if self.store.get_run(task.task_run_id) is not None:\n            raise ValueError("task_run_already_exists")\n        plan = TaskRunPlan(\n            plan_id=f"plan_reservation_{uuid4().hex}",\n            contract_type=request.contract_type,\n            status="pending",\n            metadata={\n                "reservation_only": True,\n                "runtime_profile": request.runtime_profile,\n                "normalized_actions": list(request.requested_actions),\n            },\n        )\n        run = TaskRun(\n            run_id=task.task_run_id,\n            task_id=task.task_id,\n            operation_id=task.operation_id,\n            task_run_id=task.task_run_id,\n            workspace_id=task.workspace_id,\n            project_id=task.project_id,\n            parent_task_id=task.parent_task_id,\n            current_sprint=task.current_sprint,\n            current_phase=task.current_phase,\n            bootstrap_context={\n                **task.model_dump(mode="json"),\n                "reservation_status": "durable_pending_enrichment",\n            },\n            source_type=request.source_type,\n            draft_id=request.draft_id,\n            preview_id=request.preview_id,\n            approval_id=request.approval_id,\n            session_id=request.session_id,\n            workspace=request.workspace,\n            contract_type=request.contract_type,\n            operation_type=effective_operation_type,\n            runtime_profile=request.runtime_profile,\n            capabilities_required=list(request.capabilities_required),\n            requested_actions=list(request.requested_actions),\n            intent_map=dict(request.intent_map),\n            mode=request.mode,\n            plan=plan,\n            policy_snapshot=self.store.sanitize(request.policy_decision),\n            context_injection_plan_id=request.context_injection_plan_id,\n            auto_run_requested=bool(request.start_immediately),\n        )\n        self.store.create_run(run)\n        self.events.create(\n            run.run_id,\n            "run_created",\n            "created",\n            "TaskRun identity durably reserved before runtime enrichment.",\n            metadata={\n                "source_type": run.source_type,\n                "task_id": run.task_id,\n                "task_run_id": run.run_id,\n                "operation_id": run.operation_id,\n                "workspace_id": run.workspace_id,\n                "project_id": run.project_id,\n                "parent_task_id": run.parent_task_id,\n                "workflow_id": None,\n                "contract_type": run.contract_type,\n                "auto_run_requested": run.auto_run_requested,\n                "reservation_status": "durable_pending_enrichment",\n            },\n        )\n        self.events.create(\n            run.run_id,\n            "task_bootstrap_created",\n            "created",\n            "Universal Task identity created before execution.",\n            metadata={\n                "task_id": run.task_id,\n                "task_run_id": run.run_id,\n                "operation_id": run.operation_id,\n                "runtime_profile": run.runtime_profile,\n                "workspace_id": run.workspace_id,\n                "project_id": run.project_id,\n                "current_phase": run.current_phase,\n                "workflow_id": None,\n                "parent_task_id": run.parent_task_id,\n                "execution_allowed_to_start": False,\n                "reservation_status": "durable_pending_enrichment",\n            },\n        )\n        return run\n\n'''
    text = text.replace(marker, reserve_method + marker, 1)
    text = replace_once(
        text,
        marker + '''        requested_start = bool(request.start_immediately)\n''',
        marker + '''        reserved_run = self.store.get_run(request.task_run_id) if request.task_run_id else None\n        if reserved_run is not None:\n            reservation_status = str(reserved_run.bootstrap_context.get("reservation_status") or "")\n            if reservation_status != "durable_pending_enrichment":\n                raise ValueError("task_run_already_exists")\n            if request.operation_id and reserved_run.operation_id != request.operation_id:\n                raise ValueError("task_run_reservation_operation_mismatch")\n            if request.task_id and reserved_run.task_id != request.task_id:\n                raise ValueError("task_run_reservation_task_mismatch")\n        requested_start = bool(request.start_immediately)\n''',
        label="reserved run detection",
    )
    old_store = '''        self.store.create_run(run)\n        if run.approval_id:\n'''
    new_store = '''        if reserved_run is not None:\n            latest_reserved = self.store.get_run(run.run_id) or reserved_run\n            run.created_at = latest_reserved.created_at\n            run.revision = max(run.revision, latest_reserved.revision + 1)\n            for key in ("public_response_boundary",):\n                if key in latest_reserved.intent_map:\n                    run.intent_map[key] = latest_reserved.intent_map[key]\n                if key in latest_reserved.bootstrap_context:\n                    run.bootstrap_context[key] = latest_reserved.bootstrap_context[key]\n            run.bootstrap_context["reservation_status"] = "enriched"\n            self.store.update_run(run)\n        else:\n            self.store.create_run(run)\n        if run.approval_id:\n'''
    text = replace_once(text, old_store, new_store, label="reservation enrichment persistence")
    start = text.find('''        self.events.create(\n            run.run_id,\n            "run_created",\n''')
    if start < 0:
        raise RuntimeError("run_created event block not found")
    end_marker = '''        self.events.create(\n            run.run_id,\n            "PlanningStarted",\n'''
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError("PlanningStarted marker not found")
    event_block = text[start:end]
    indented = "".join(("    " + line if line.strip() else line) for line in event_block.splitlines(keepends=True))
    text = text[:start] + '''        if reserved_run is None:\n''' + indented + text[end:]
    save(path, text)


def patch_readonly_runtime() -> None:
    path, text = load("src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py")
    text = replace_once(
        text,
        '''    def start_public_boundary(\n        self,\n        *,\n        request,\n        workspace: str,\n        label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY",\n    ) -> ReadonlyArtifactExecution:\n''',
        '''    def start_public_boundary(\n        self,\n        *,\n        request,\n        workspace: str,\n        label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY",\n        operation_id: str | None = None,\n    ) -> ReadonlyArtifactExecution:\n''',
        label="public boundary operation id",
    )
    text = replace_once(
        text,
        '''            return self.execute(request=request, workspace=workspace, label=label)\n''',
        '''            return self.execute(request=request, workspace=workspace, label=label, operation_id=operation_id)\n''',
        label="public boundary synchronous operation id",
    )
    text = replace_once(
        text,
        '''                holder["execution"] = self.execute(request=request, workspace=workspace, label=label)\n''',
        '''                holder["execution"] = self.execute(\n                    request=request,\n                    workspace=workspace,\n                    label=label,\n                    operation_id=operation_id,\n                )\n''',
        label="public boundary worker operation id",
    )
    old_poll = '''            runtime_create_in_progress = bool(holder.get("runtime_create_started")) and not bool(holder.get("runtime_create_completed"))\n            direct_store_create = bool(holder.get("store_run_id")) and not bool(holder.get("runtime_create_started"))\n            if discovered_run is not None and (not runtime_create_in_progress or direct_store_create):\n'''
    new_poll = '''            runtime_create_in_progress = bool(holder.get("runtime_create_started")) and not bool(holder.get("runtime_create_completed"))\n            direct_store_create = bool(holder.get("store_run_id")) and not bool(holder.get("runtime_create_started"))\n            durable_reservation = bool(\n                discovered_run is not None\n                and str(discovered_run.bootstrap_context.get("reservation_status") or "")\n                in {"durable_pending_enrichment", "enriched"}\n            )\n            if discovered_run is not None and (durable_reservation or not runtime_create_in_progress or direct_store_create):\n'''
    text = replace_once(text, old_poll, new_poll, label="public boundary durable reservation acceptance")
    text = replace_once(
        text,
        '''                reason_code=self.public_preacceptance_policy.create_run_not_reached_reason_code,\n                policy=policy,\n            ),\n''',
        '''                reason_code=self.public_preacceptance_policy.create_run_not_reached_reason_code,\n                policy=policy,\n                operation_id=operation_id,\n            ),\n''',
        label="timeout operation continuity",
    )
    text = replace_once(
        text,
        '''    def execute(\n        self,\n        *,\n        request,\n        workspace: str,\n        label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY",\n    ) -> ReadonlyArtifactExecution:\n''',
        '''    def execute(\n        self,\n        *,\n        request,\n        workspace: str,\n        label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY",\n        operation_id: str | None = None,\n    ) -> ReadonlyArtifactExecution:\n''',
        label="readonly execute operation id",
    )
    pattern = re.compile(
        r'''        run = self\.runtime\.create_run\(\n            TaskRunRequest\(\n(?P<body>.*?)                start_immediately=False,\n            \)\n        \)\n''',
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError("readonly TaskRunRequest creation block not found")
    if len(pattern.findall(text)) != 1:
        raise RuntimeError("readonly TaskRunRequest creation block is not unique")
    body = match.group("body")
    if '                operation_id=' not in body:
        body = body.replace(
            '                session_id=request.session_id,\n',
            '                session_id=request.session_id,\n                operation_id=operation_id,\n',
            1,
        )
    replacement = (
        '        run_request = TaskRunRequest(\n'
        + body
        + '            start_immediately=False,\n'
        + '        )\n'
        + '        reservation = self.runtime.reserve_run(run_request)\n'
        + '        run_request = run_request.model_copy(\n'
        + '            update={\n'
        + '                "task_id": reservation.task_id,\n'
        + '                "task_run_id": reservation.run_id,\n'
        + '                "operation_id": reservation.operation_id,\n'
        + '                "workspace_id": reservation.workspace_id,\n'
        + '                "project_id": reservation.project_id,\n'
        + '            }\n'
        + '        )\n'
        + '        run = self.runtime.create_run(run_request)\n'
    )
    text = text[:match.start()] + replacement + text[match.end():]
    timeout_sig = '''    def _timeout_blocked_response(\n        self,\n        request,\n        *,\n        workspace: str,\n        reason_code: str,\n        policy: PublicRuntimeResponsePolicy,\n    ) -> ChatResponse:\n'''
    timeout_new = '''    def _timeout_blocked_response(\n        self,\n        request,\n        *,\n        workspace: str,\n        reason_code: str,\n        policy: PublicRuntimeResponsePolicy,\n        operation_id: str | None = None,\n    ) -> ChatResponse:\n'''
    text = replace_once(text, timeout_sig, timeout_new, label="timeout response operation id signature")
    timeout_response_anchor = '''            response_id=f"chat_timeout_blocked_{uuid4().hex}",\n            session_id=request.session_id,\n            operation_type="workspace_analysis_readonly",\n'''
    timeout_response_new = '''            response_id=f"chat_timeout_blocked_{uuid4().hex}",\n            session_id=request.session_id,\n            operation_id=operation_id,\n            operation_type="workspace_analysis_readonly",\n'''
    text = replace_once(text, timeout_response_anchor, timeout_response_new, label="timeout response operation id field")
    text = replace_once(
        text,
        '''                "requires_task": False,\n                "readonly": True,\n''',
        '''                "requires_task": True,\n                "readonly": True,\n''',
        label="timeout preserves task requirement",
    )
    final_op = '''            operation_id=f"chatop_{run_id.replace('task_run_', '')}",\n            operation_type="workspace_analysis_readonly",\n'''
    final_op_new = '''            operation_id=(\n                self.runtime.store.get_run(run_id).operation_id\n                if self.runtime.store.get_run(run_id) is not None\n                else None\n            ),\n            operation_type="workspace_analysis_readonly",\n'''
    text = replace_once(text, final_op, final_op_new, label="task-bound final operation continuity")
    accepted_anchor = '''                "task_run_id": run.run_id,\n                "run_status": run.status,\n                "safe_to_report_success": False,\n'''
    accepted_new = '''                "task_run_id": run.run_id,\n                "operation_id": run.operation_id,\n                "contract_type": run.contract_type,\n                "runtime_profile": run.runtime_profile,\n                "requires_task": True,\n                "read_only": True,\n                "artifact_generation": True,\n                "workspace_mutation": False,\n                "run_status": run.status,\n                "safe_to_report_success": False,\n'''
    text = replace_once(text, accepted_anchor, accepted_new, label="accepted response semantic contract")
    save(path, text)


def write_regressions() -> None:
    path = ROOT / "tests/unit/test_runtime_identity_acceptance_regression.py"
    path.write_text(
        '''from __future__ import annotations\n\nimport time\n\nfrom aipinho.schemas.chat.chat_request import ChatRequest\nfrom aipinho.schemas.chat.chat_response import ChatResponse\nfrom aipinho.schemas.runtime.task_run_request import TaskRunRequest\nfrom aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService\nfrom aipinho.services.governance.lifecycle.public_route_lifecycle_service import PublicRouteLifecycleService\nfrom aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (\n    PublicRuntimeResponsePolicy,\n    ReadonlyAnalysisArtifactRuntimeService,\n)\n\n\nclass _SlowPlanner:\n    def __init__(self, delegate, delay: float = 0.25) -> None:\n        self.delegate = delegate\n        self.delay = delay\n\n    def plan(self, request):\n        time.sleep(self.delay)\n        return self.delegate.plan(request)\n\n\ndef test_readonly_artifact_contract_preserves_execution_semantics() -> None:\n    snapshot = GovernanceLifecycleService().evaluate(\n        user_text=(\n            "Analise este workspace em modo somente leitura e gere o artifact "\n            "reports/example/analysis.md sem modificar o workspace."\n        ),\n        source_channel="chat",\n        session_id="generic_readonly_artifact",\n        workspace_path=r"C:\\Workspace\\Generic",\n    )\n\n    contract = snapshot.operation_contract\n    assert contract.operation_type == "workspace_analysis_readonly"\n    assert contract.contract_type == "analysis_readonly"\n    assert contract.runtime_profile == "readonly_analysis"\n    assert contract.read_only is True\n    assert contract.requires_task is True\n    assert contract.artifact_generation is True\n    assert contract.workspace_mutation is False\n    assert snapshot.policy.permission.value == "allowed"\n    assert snapshot.policy.requires_approval is False\n    assert snapshot.execution_plan.executable is True\n    assert snapshot.execution_plan.executable_plan_ref == f"readonly_analysis:{contract.operation_id}"\n\n\ndef test_pure_readonly_planning_remains_nonexecuting() -> None:\n    snapshot = GovernanceLifecycleService().evaluate(\n        user_text="Somente planejamento textual: explique uma estrategia, sem executar e sem criar artefatos.",\n        source_channel="chat",\n        session_id="generic_readonly_plan",\n    )\n\n    contract = snapshot.operation_contract\n    assert contract.requires_task is False\n    assert contract.artifact_generation is False\n    assert contract.workspace_mutation is False\n    assert snapshot.execution_plan.executable is False\n    assert snapshot.state.value == "plan_only_preview"\n\n\ndef test_reserved_run_is_durable_before_slow_enrichment_and_reuses_identity(task_runtime_service, tmp_path) -> None:\n    original_planner = task_runtime_service.planner\n    task_runtime_service.planner = _SlowPlanner(original_planner)\n    service = ReadonlyAnalysisArtifactRuntimeService(\n        runtime=task_runtime_service,\n        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=80),\n    )\n    operation_id = "op_generic_ingress_continuity"\n    request = ChatRequest(\n        message="Analise em somente leitura e gere reports/example/analysis.md",\n        session_id="generic_early_acceptance",\n    )\n\n    started = time.monotonic()\n    execution = service.start_public_boundary(\n        request=request,\n        workspace=str(tmp_path),\n        operation_id=operation_id,\n    )\n    elapsed = time.monotonic() - started\n\n    assert elapsed < 0.20\n    assert execution.response.status == "accepted_running"\n    assert execution.run_id is not None\n    assert execution.response.task_run_id == execution.run_id\n    assert execution.response.operation_id == operation_id\n    durable = task_runtime_service.store.get_run(execution.run_id)\n    assert durable is not None\n    assert durable.operation_id == operation_id\n    assert durable.task_run_id == execution.run_id\n\n    deadline = time.monotonic() + 3.0\n    while time.monotonic() < deadline:\n        enriched = task_runtime_service.store.get_run(execution.run_id)\n        if enriched and enriched.bootstrap_context.get("reservation_status") == "enriched":\n            break\n        time.sleep(0.02)\n    enriched = task_runtime_service.store.get_run(execution.run_id)\n    assert enriched is not None\n    assert enriched.operation_id == operation_id\n    assert enriched.bootstrap_context.get("reservation_status") == "enriched"\n    events = task_runtime_service.store.get_events(execution.run_id)\n    assert len([event for event in events if event.type == "run_created"]) == 1\n    assert len([event for event in events if event.type == "task_bootstrap_created"]) == 1\n\n\ndef test_task_runtime_reservation_cannot_be_rebound_to_another_operation(task_runtime_service, tmp_path) -> None:\n    request = TaskRunRequest(\n        source_type="direct",\n        session_id="generic_reservation_guard",\n        workspace=str(tmp_path),\n        operation_id="op_original",\n        contract_type="analysis_readonly",\n        operation_type="workspace_analysis_readonly",\n        runtime_profile="readonly_analysis",\n        capabilities_required=["read_workspace", "artifact_generate"],\n        requested_actions=["read_workspace"],\n        intent_map={"intent_type": "workspace_analysis_readonly"},\n        mode="read_only",\n    )\n    reserved = task_runtime_service.reserve_run(request)\n    rebound = request.model_copy(\n        update={\n            "task_id": reserved.task_id,\n            "task_run_id": reserved.run_id,\n            "operation_id": "op_other",\n        }\n    )\n\n    try:\n        task_runtime_service.create_run(rebound)\n    except ValueError as exc:\n        assert str(exc) == "task_run_reservation_operation_mismatch"\n    else:\n        raise AssertionError("reservation operation identity must be immutable")\n\n\ndef test_public_finalization_preserves_existing_operation_id() -> None:\n    operation_id = "op_existing_public_operation"\n    response = ChatResponse(\n        response_id="chat_existing_operation",\n        session_id="generic_finalize_identity",\n        operation_id=operation_id,\n        operation_type="workspace_analysis_readonly",\n        message_type="task_status_update",\n        status="accepted_running",\n        message="Accepted",\n        intent={\n            "intent_type": "workspace_analysis_readonly",\n            "requires_task": True,\n            "readonly": True,\n        },\n        policy={\n            "artifact_generation": True,\n            "workspace_write": False,\n            "safe_to_report_success": False,\n        },\n        contract_preview={\n            "contract_type": "analysis_readonly",\n            "runtime_profile": "readonly_analysis",\n            "requires_task": True,\n            "artifact_generation": True,\n            "workspace_mutation": False,\n        },\n        is_final_answer=False,\n        grounded=True,\n    )\n\n    finalized = PublicRouteLifecycleService().finalize_chat_response(\n        response,\n        prompt="Analise em somente leitura e gere reports/example/analysis.md",\n        source_channel="chat",\n        workspace_path=r"C:\\Workspace\\Generic",\n    )\n\n    assert finalized.operation_id == operation_id\n    assert finalized.governance_lifecycle["operation_contract"]["operation_id"] == operation_id\n''',
        encoding="utf-8",
    )


def main() -> None:
    patch_lifecycle_schema()
    patch_governance_lifecycle()
    patch_policy()
    patch_canonical_runtime()
    patch_public_route_lifecycle()
    patch_public_chat()
    patch_task_runtime()
    patch_readonly_runtime()
    write_regressions()
    print("PATCH_STATUS=APPLIED")


if __name__ == "__main__":
    main()
