from aipinho.schemas.runtime.kernel import KernelModule, ModuleContext
from aipinho.services.runtime.runtime_kernel_service import KernelRegistryService, KernelValidationSuite, ModuleLifecycle, ModuleLoader, RuntimeKernel, RuntimePipeline


def test_kr1_runtime_kernel_boots_and_registers_modules():
    kernel = RuntimeKernel()
    health = kernel.boot()
    registry = kernel.registry()

    assert health.status == "ok"
    assert health.state == "READY"
    assert "planner" in registry.modules
    assert "semantic_interpreter" in registry.modules
    assert all(module.status == "ready" for module in registry.modules.values())
    assert all(module.requires_contract for module in registry.modules.values())
    assert registry.events


def test_kr1_kernel_registry_blocks_missing_dependencies():
    registry = KernelRegistryService()
    registry.register(KernelModule(module_id="orphan", name="Orphan", dependencies=["missing"], contracts_supported=["x"]))
    registry.validate()
    health = registry.health()

    assert registry.registry.modules["orphan"].status == "blocked"
    assert health.status == "degraded"
    assert "orphan" in health.blocked_modules


def test_kr2_module_loader_and_lifecycle_contracts():
    loader = ModuleLoader()
    lifecycle = ModuleLifecycle()
    modules = loader.default_modules()
    executor = next(module for module in modules if module.module_id == "executor")
    context = RuntimeKernel().context
    initialized = lifecycle.initialize(executor, context=ModuleContext(kernel_id=context.kernel_id, module_id=executor.module_id, state=context.state))

    assert len(modules) >= 10
    assert executor.can_execute is True
    assert executor.can_write is False
    assert "execution_result" in executor.contracts_supported
    assert initialized.status == "ready"
    assert lifecycle.execute(executor)["status"] == "not_executed"


def test_kr3_runtime_pipeline_contains_canonical_order_without_skips():
    kernel = RuntimeKernel()
    kernel.boot()
    trace = RuntimePipeline().trace(kernel.context.kernel_id, completed_stages=RuntimePipeline.CANONICAL_STAGES)

    assert [stage.name for stage in trace.stages] == RuntimePipeline.CANONICAL_STAGES
    assert trace.complete is True
    assert trace.valid is True
    assert trace.skipped_stages == []
    assert trace.mutates_runtime is False


def test_kr4_kernel_validation_suite_covers_boot_registry_pipeline_dispatch_and_failure():
    report = KernelValidationSuite().validate()

    assert report.verdict == "KR4_READY"
    assert report.coverage["boot"] is True
    assert report.coverage["registry"] is True
    assert report.coverage["pipeline"] is True
    assert report.coverage["contracts"] is True
    assert report.coverage["failure"] is True
    assert report.mutates_runtime is False


def test_runtime_kernel_dispatch_requires_registered_module_and_contract():
    kernel = RuntimeKernel()
    kernel.boot()

    assert kernel.dispatch("planner")["reason"] == "runtime_contract_required"
    assert kernel.dispatch("planner", contract={"contract_type": "execution_plan"})["status"] == "ready"
    assert kernel.dispatch("unknown", contract={"contract_type": "execution_plan"})["reason"] == "kernel_module_not_registered"
