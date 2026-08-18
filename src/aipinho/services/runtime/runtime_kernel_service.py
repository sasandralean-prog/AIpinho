from __future__ import annotations

import time

from aipinho.schemas.runtime.kernel import (
    KernelContext,
    KernelEvent,
    KernelHealthReport,
    KernelModule,
    KernelRegistry,
    KernelRuntimeReport,
    ModuleCapabilities,
    ModuleContext,
    PipelineStage,
    PipelineTrace,
)


class KernelRegistryService:
    def __init__(self, context: KernelContext | None = None) -> None:
        self.context = context or KernelContext()
        self.registry = KernelRegistry(kernel_id=self.context.kernel_id)

    def register(self, module: KernelModule) -> KernelModule:
        if module.module_id in self.registry.modules:
            raise ValueError(f"kernel_module_already_registered:{module.module_id}")
        self.registry.modules[module.module_id] = module
        self.registry.events.append(
            KernelEvent(event_type="module_registered", kernel_id=self.context.kernel_id, module_id=module.module_id, message="Module registered in Runtime Kernel.")
        )
        return module

    def validate(self) -> KernelRegistry:
        for module in list(self.registry.modules.values()):
            missing = [dependency for dependency in module.dependencies if dependency not in self.registry.modules]
            status = "blocked" if missing else "ready"
            health = "blocked" if missing else "ok"
            self.registry.modules[module.module_id] = module.model_copy(update={"status": status, "health": health, "metadata": {**module.metadata, "missing_dependencies": missing}})
            self.registry.events.append(
                KernelEvent(
                    event_type="module_validated",
                    kernel_id=self.context.kernel_id,
                    module_id=module.module_id,
                    status=health,
                    message="Module validation completed.",
                    metadata={"missing_dependencies": missing},
                )
            )
        return self.registry

    def health(self, boot_time_ms: float = 0.0) -> KernelHealthReport:
        modules = self.registry.modules
        blocked = sorted(module_id for module_id, module in modules.items() if module.status == "blocked")
        active = sorted(module_id for module_id, module in modules.items() if module.status in {"registered", "ready"})
        return KernelHealthReport(
            kernel_id=self.context.kernel_id,
            state="FAILED" if blocked else self.context.state,
            active_modules=active,
            blocked_modules=blocked,
            dependencies={module_id: module.dependencies for module_id, module in sorted(modules.items())},
            boot_time_ms=boot_time_ms,
            status="degraded" if blocked else "ok",
            warnings=[f"module_dependency_missing:{module_id}" for module_id in blocked],
        )


class ModuleLifecycle:
    def initialize(self, module: KernelModule, context: ModuleContext) -> KernelModule:
        return module.model_copy(update={"status": "ready", "health": "ok", "metadata": {**module.metadata, "initialized_in": context.kernel_id}})

    def validate(self, module: KernelModule) -> KernelModule:
        if module.requires_contract and not module.contracts_supported:
            return module.model_copy(update={"status": "blocked", "health": "blocked", "metadata": {**module.metadata, "validation_error": "contracts_supported_required"}})
        return module

    def execute(self, module: KernelModule) -> dict[str, object]:
        return {"status": "not_executed", "module_id": module.module_id, "reason": "kernel_module_execution_requires_runtime_contract"}

    def shutdown(self, module: KernelModule) -> KernelModule:
        return module.model_copy(update={"status": "shutdown", "health": "shutdown"})

    def health(self, module: KernelModule) -> dict[str, object]:
        return {"module_id": module.module_id, "status": module.status, "health": module.health}

    def metadata(self, module: KernelModule) -> dict[str, object]:
        return module.model_dump(mode="json")


class ModuleLoader:
    def default_modules(self) -> list[KernelModule]:
        return [
            self._module("semantic_interpreter", "Semantic Interpreter", ["semantic_understanding"], ["semantic_ir"]),
            self._module("normalizer", "Semantic Normalizer", ["semantic_normalization"], ["semantic_ir"]),
            self._module("contract_compiler", "Contract Compiler", ["contract_compilation"], ["runtime_contract_bundle"], dependencies=["semantic_interpreter", "normalizer"]),
            self._module("governance_controller", "Governance Controller", ["cognitive_governance", "policy"], ["governance_decision"], dependencies=["contract_compiler"]),
            self._module("planner", "Planner", ["planning"], ["execution_plan"], dependencies=["governance_controller"]),
            self._module("approval", "Approval", ["approval"], ["approval_contract"], dependencies=["planner"]),
            self._module("executor", "Executor", ["execution"], ["execution_result"], dependencies=["approval"], can_execute=True),
            self._module("validator", "Validator", ["validation"], ["validation_result"], dependencies=["executor"]),
            self._module("completion", "Completion", ["completion"], ["completion_result"], dependencies=["validator"]),
            self._module("speaker", "Speaker", ["speaker_truth"], ["speaker_truth_response"], dependencies=["completion"]),
            self._module("runtime_doctor", "Runtime Doctor", ["runtime_diagnostics"], ["runtime_doctor_report"], dependencies=["completion"]),
            self._module("patch_planner", "Patch Planner", ["patch_planning"], ["patch_plan"], dependencies=["runtime_doctor"]),
            self._module("reviewer", "Reviewer", ["review"], ["review_result"], dependencies=["executor"]),
            self._module("reporter", "Reporter", ["reporting"], ["artifact_report"], dependencies=["completion"]),
            self._module("supervisor", "Supervisor", ["supervision"], ["supervisor_decision"], dependencies=["governance_controller"]),
        ]

    def _module(
        self,
        module_id: str,
        name: str,
        capabilities: list[str],
        contracts_supported: list[str],
        dependencies: list[str] | None = None,
        can_execute: bool = False,
    ) -> KernelModule:
        module_capabilities = ModuleCapabilities(
            can_read=True,
            can_write=False,
            can_execute=can_execute,
            contracts_supported=contracts_supported,
            required_permissions=["runtime_contract"] if can_execute else [],
        )
        return KernelModule(
            module_id=module_id,
            name=name,
            capabilities=capabilities,
            contracts=contracts_supported,
            dependencies=dependencies or [],
            can_read=module_capabilities.can_read,
            can_write=module_capabilities.can_write,
            can_execute=module_capabilities.can_execute,
            contracts_supported=module_capabilities.contracts_supported,
            required_permissions=module_capabilities.required_permissions,
        )


class RuntimeKernel:
    def __init__(self, loader: ModuleLoader | None = None, lifecycle: ModuleLifecycle | None = None) -> None:
        self.context = KernelContext()
        self.registry_service = KernelRegistryService(context=self.context)
        self.loader = loader or ModuleLoader()
        self.lifecycle = lifecycle or ModuleLifecycle()

    def boot(self) -> KernelHealthReport:
        started = time.monotonic()
        self.context = self.context.model_copy(update={"state": "INIT"})
        self.registry_service.registry.events.append(KernelEvent(event_type="kernel_boot", kernel_id=self.context.kernel_id, message="Runtime Kernel boot started."))
        for module in self.loader.default_modules():
            context = ModuleContext(kernel_id=self.context.kernel_id, module_id=module.module_id, state=self.context.state)
            initialized = self.lifecycle.validate(self.lifecycle.initialize(module, context))
            self.registry_service.register(initialized)
        self.registry_service.validate()
        health = self.registry_service.health(boot_time_ms=round((time.monotonic() - started) * 1000, 3))
        self.context = self.context.model_copy(update={"state": "FAILED" if health.blocked_modules else "READY"})
        return health.model_copy(update={"state": self.context.state})

    def registry(self) -> KernelRegistry:
        return self.registry_service.registry

    def dispatch(self, module_id: str, contract: dict[str, object] | None = None) -> dict[str, object]:
        module = self.registry().modules.get(module_id)
        if module is None:
            return {"status": "blocked", "reason": "kernel_module_not_registered", "module_id": module_id}
        if module.requires_contract and not contract:
            return {"status": "blocked", "reason": "runtime_contract_required", "module_id": module_id}
        return {"status": "ready", "module_id": module_id, "contract_received": bool(contract)}


class RuntimePipeline:
    CANONICAL_STAGES = [
        "Prompt",
        "Semantic Interpreter",
        "Semantic IR",
        "Normalizer",
        "Contract Compiler",
        "Governance",
        "Planning",
        "Approval",
        "Execution",
        "Validation",
        "Completion",
        "Speaker",
    ]

    def trace(self, kernel_id: str, completed_stages: list[str] | None = None) -> PipelineTrace:
        completed = set(completed_stages or [])
        stages = [
            PipelineStage(
                stage_id=f"stage_{index:02d}_{self._slug(name)}",
                name=name,
                input_contracts=[] if index == 1 else [self._slug(self.CANONICAL_STAGES[index - 2])],
                output_contracts=[self._slug(name)],
                rollback="return_to_previous_stage" if index > 1 else "not_applicable",
                status="completed" if name in completed else "ready",
            )
            for index, name in enumerate(self.CANONICAL_STAGES, start=1)
        ]
        skipped = [stage.name for stage in stages if stage.name not in self.CANONICAL_STAGES]
        return PipelineTrace(kernel_id=kernel_id, stages=stages, skipped_stages=skipped, complete=len(completed) == len(self.CANONICAL_STAGES), valid=not skipped)

    def _slug(self, value: str) -> str:
        return value.lower().replace(" ", "_")


class KernelValidationSuite:
    def validate(self) -> KernelRuntimeReport:
        kernel = RuntimeKernel()
        health = kernel.boot()
        registry = kernel.registry()
        pipeline = RuntimePipeline().trace(kernel.context.kernel_id, completed_stages=RuntimePipeline.CANONICAL_STAGES)
        dispatch = kernel.dispatch("planner", contract={"contract_type": "execution_plan"})
        missing = kernel.dispatch("missing_module", contract={"contract_type": "execution_plan"})
        coverage = {
            "boot": health.status == "ok",
            "registry": bool(registry.modules),
            "pipeline": pipeline.valid and len(pipeline.stages) == len(RuntimePipeline.CANONICAL_STAGES),
            "modules": all(module.status == "ready" for module in registry.modules.values()),
            "contracts": dispatch["status"] == "ready",
            "failure": missing["status"] == "blocked",
            "health": health.status == "ok",
        }
        verdict = "KR4_READY" if all(coverage.values()) else "KR4_REQUIRES_PATCH"
        return KernelRuntimeReport(
            kernel_id=kernel.context.kernel_id,
            boot="passed" if coverage["boot"] else "failed",
            registry="passed" if coverage["registry"] else "failed",
            pipeline="passed" if coverage["pipeline"] else "failed",
            modules="passed" if coverage["modules"] else "failed",
            contracts="passed" if coverage["contracts"] else "failed",
            validation="passed" if all(coverage.values()) else "failed",
            health=health,
            coverage=coverage,
            verdict=verdict,
        )
