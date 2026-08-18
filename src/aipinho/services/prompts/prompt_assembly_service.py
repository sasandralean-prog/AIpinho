from __future__ import annotations

from typing import Any

from aipinho.schemas.models.generation_config import GenerationConfig
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.prompts.prompt_assembly import PromptAssembly, PromptAssemblyRequest, PromptPreview
from aipinho.schemas.prompts.prompt_context_item import PromptContextItem
from aipinho.schemas.prompts.prompt_message import PromptMessage
from aipinho.schemas.rag.integration.contracts import ContextInjectionPlan
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.prompts.context_packing_service import ContextPackingService
from aipinho.services.prompts.output_contract_builder import OutputContractBuilder
from aipinho.services.prompts.prompt_budget_service import PromptBudgetService
from aipinho.services.prompts.prompt_trace_service import PromptTraceService
from aipinho.services.prompts.role_prompt_builder import RolePromptBuilder
from aipinho.services.evaluation.output_contract_validator import OutputContractValidator
from aipinho.services.prompts.safety_envelope_builder import SafetyEnvelopeBuilder
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator


class PromptAssemblyService:
    def __init__(
        self,
        budget_service: PromptBudgetService | None = None,
        context_packing: ContextPackingService | None = None,
        role_builder: RolePromptBuilder | None = None,
        contract_builder: OutputContractBuilder | None = None,
        safety_builder: SafetyEnvelopeBuilder | None = None,
        model_router: ModelRouterService | None = None,
        trace_service: PromptTraceService | None = None,
        context_planner: ContextInjectionPlanner | None = None,
        context_validator: ContextUsageValidator | None = None,
    ) -> None:
        self.budget_service = budget_service or PromptBudgetService()
        self.context_packing = context_packing or ContextPackingService()
        self.role_builder = role_builder or RolePromptBuilder()
        self.contract_builder = contract_builder or OutputContractBuilder()
        self.safety_builder = safety_builder or SafetyEnvelopeBuilder()
        self.model_router = model_router or ModelRouterService()
        self.trace_service = trace_service or PromptTraceService()
        self.context_planner = context_planner or ContextInjectionPlanner()
        self.context_validator = context_validator or ContextUsageValidator()

    def assemble(self, request: PromptAssemblyRequest) -> PromptAssembly:
        trace: list[dict[str, Any]] = []
        warnings: list[str] = []
        trace.append(self.trace_service.item("request", "ok", "prompt_assembly_request_received", data={"purpose": request.purpose, "role_id": request.role_id}))

        contract = self.contract_builder.get_contract(request.output_contract_type)
        contract_check = self.contract_builder.validate_contract(contract)
        if not contract_check.get("valid"):
            warnings.append(str(contract_check.get("error") or "output_contract_invalid"))
        trace.append(self.trace_service.item("output_contract", "ok" if contract_check.get("valid") else "degraded", str(contract_check.get("error") or contract.contract_type)))

        safety = self.safety_builder.build(
            purpose=request.purpose,
            policy_decision=request.policy_decision,
            role_id=request.role_id,
            output_contract_type=contract.contract_type,
        )
        warnings.extend(safety.warnings)

        role_message, role_warnings = self.role_builder.build_role_message(request.role_id)
        warnings.extend(role_warnings)

        if request.retrieval_context_bundle:
            warnings.append("direct_retrieval_context_requires_plan")
        context_plan, plan_warnings = self._resolve_context_plan(request)
        warnings.extend(plan_warnings)
        context_items = self._collect_context_items(request, context_plan)
        budget = self.budget_service.budget_for(request.purpose)
        packed_items, budget, pack_warnings = self.context_packing.pack(context_items, budget)
        warnings.extend(pack_warnings)
        trace.append(self.trace_service.item("context_packing", "ok", "context_packed", data={"input_items": len(context_items), "packed_items": len(packed_items), "omitted_items": list(budget.omitted_items)}))

        messages = self._build_messages(
            request=request,
            safety_message=self.safety_builder.build_message(safety),
            role_message=role_message,
            contract_message=self.contract_builder.build_contract_message(contract),
            packed_items=packed_items,
        )
        budget = self.budget_service.summarize_budget(messages, packed_items, budget)

        if budget.used_input_chars > budget.max_input_chars:
            budget.truncated = True
            warnings.append("prompt_budget_exceeded")

        route_decision = self.model_router.select_model(
            requested_model_id=request.model_id,
            purpose=request.purpose,
            role_id=request.role_id,
        )
        if route_decision.status != "ok":
            warnings.append("model_route_blocked:" + route_decision.reason)
        warnings.extend(route_decision.warnings)
        trace.append(self.trace_service.item("model_route", route_decision.status, route_decision.reason, data=route_decision.as_dict()))

        return PromptAssembly(
            purpose=request.purpose,
            model_id=route_decision.model.model_id if route_decision.model else request.model_id,
            role_id=request.role_id,
            messages=messages,
            context_items=packed_items,
            budget=budget,
            output_contract=contract,
            safety_envelope=safety,
            warnings=list(dict.fromkeys(warnings)),
            trace=trace if request.include_trace else [],
        )

    def preview(self, request: PromptAssemblyRequest) -> PromptPreview:
        assembly = self.assemble(request)
        route_decision = self.model_router.select_model(
            requested_model_id=assembly.model_id,
            purpose=assembly.purpose,
            role_id=assembly.role_id,
        )
        provider_id = route_decision.provider.provider_id if route_decision.provider else "stub.local"
        model_request = ModelRequest(
            model_id=assembly.model_id,
            provider_id=provider_id,
            messages=assembly.messages,
            generation_config=GenerationConfig(max_tokens=assembly.budget.max_output_tokens),
            output_contract=assembly.output_contract.model_dump(),
            safety_envelope=assembly.safety_envelope.model_dump(),
            trace=assembly.trace,
            metadata={
                "assembly_id": assembly.assembly_id,
                "purpose": assembly.purpose,
                "role_id": assembly.role_id,
                "warnings": assembly.warnings,
                "real_inference_requested": False,
                "model_provider": provider_id,
                "safety_envelope_id": assembly.safety_envelope.envelope_id,
                "output_contract_type": assembly.output_contract.contract_type,
                "budget_summary": assembly.budget.model_dump(),
                "context_items": len(assembly.context_items),
                "evidence_items": len([item for item in assembly.context_items if item.source_type == "evidence"]),
            },
        )
        return PromptPreview(assembly=assembly, model_request=model_request, invokes_model=False, side_effects=False)

    def estimate_budget(self, request: PromptAssemblyRequest) -> dict[str, object]:
        assembly = self.assemble(request)
        return {
            "status": "ok",
            "purpose": assembly.purpose,
            "budget": assembly.budget.model_dump(),
            "warnings": assembly.warnings,
        }

    def validate_output_contract(self, contract_type: str, content: str) -> dict[str, object]:
        contract = self.contract_builder.get_contract(contract_type)
        return {
            "status": "ok",
            "contract": contract.model_dump(),
            "validation": self.contract_builder.validate_model_response_against_contract(content, contract),
        }

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "prompt_assembly",
            "real_inference_enabled": False,
            "memory_auto_injection_enabled": False,
            "curated_memory_available_for_explicit_read": True,
            "retrieval_enabled": True,
            "retrieval_mode": "governed_read_only",
            "retrieval_auto_injection_enabled": False,
            "retrieval_explicit_context_bundle_enabled": False,
            "context_injection_plan_required": True,
            "context_injection_plan_enabled": True,
            "components": {
                "budget": self.budget_service.status(),
                "context_packing": self.context_packing.status(),
                "role_prompt": self.role_builder.status(),
                "output_contract": self.contract_builder.status(),
                "safety_envelope": self.safety_builder.status(),
                "model_router": self.model_router.status(),
            },
        }

    def _build_messages(
        self,
        *,
        request: PromptAssemblyRequest,
        safety_message: PromptMessage,
        role_message: PromptMessage,
        contract_message: PromptMessage,
        packed_items: list[PromptContextItem],
    ) -> list[PromptMessage]:
        messages = [safety_message, role_message]
        policy_content = self._dict_to_block("Policy decision", request.policy_decision)
        if policy_content:
            messages.append(PromptMessage(role="developer", content=policy_content, metadata={"source": "policy_decision"}))
        messages.append(contract_message)
        for item in packed_items:
            messages.append(
                PromptMessage(
                    role="developer",
                    content=f"Context item: {item.title}\nSource: {item.source_type}\n{item.content}",
                    metadata={"context_item_id": item.item_id, "source_type": item.source_type, **item.metadata},
                )
            )
        messages.append(PromptMessage(role="user", content=request.user_message or "Preview the assembled prompt.", metadata={"purpose": request.purpose}))
        return messages

    def _collect_context_items(
        self,
        request: PromptAssemblyRequest,
        context_plan: ContextInjectionPlan | None,
    ) -> list[PromptContextItem]:
        items = list(request.context_items)
        self._append_dict_item(items, "intent", "Intent map", request.intent_map, priority=0.9)
        self._append_dict_item(items, "policy", "Policy decision", request.policy_decision, priority=0.95)
        self._append_dict_item(items, "session", "Session context", request.session_context, priority=0.55)
        self._append_file_bundle(items, request.file_context_bundle)
        self._append_project_report(items, request.project_report)
        self._append_context_injection_plan(items, context_plan)
        for index, evidence in enumerate(request.evidence):
            self._append_dict_item(items, "evidence", f"Evidence {index + 1}", evidence, priority=0.8)
        return items

    def _resolve_context_plan(
        self,
        request: PromptAssemblyRequest,
    ) -> tuple[ContextInjectionPlan | None, list[str]]:
        if request.context_injection_plan:
            try:
                plan = ContextInjectionPlan.model_validate(request.context_injection_plan)
            except Exception:
                return None, ["context_injection_plan_invalid"]
        elif request.context_injection_plan_id:
            try:
                plan = self.context_planner.get_plan(request.context_injection_plan_id)
            except ValueError:
                return None, ["context_injection_plan_id_invalid"]
            if plan is None:
                return None, ["context_injection_plan_not_found"]
        else:
            return None, []
        validation = self.context_validator.validate_plan(plan)
        if not validation.valid:
            return None, ["context_injection_plan_unsafe", *validation.violations]
        return plan, list(validation.warnings)

    def _append_context_injection_plan(
        self,
        items: list[PromptContextItem],
        plan: ContextInjectionPlan | None,
    ) -> None:
        if plan is None:
            return
        citation_ids = sorted(plan.citation_map.citations)
        source_lines = [
            f"- {entry.get('source_type')}:{entry.get('source_id')} ({entry.get('items')} item(s))"
            for entry in plan.source_summary
        ]
        citation_lines = [
            f"- {citation_id}: {(citation.get('source_ref') or {}).get('ref')}"
            for citation_id, citation in sorted(plan.citation_map.citations.items())
        ]
        header = "\n".join(
            [
                "Governed Context",
                "Use this context only for the stated purpose and cite the provided citation IDs for contextual claims.",
                "Sources:",
                *(source_lines or ["- none"]),
                "Citation map:",
                *(citation_lines or ["- none"]),
                "Limitations:",
                *([f"- {value}" for value in plan.limitations] or ["- none"]),
            ]
        )
        items.append(
            PromptContextItem(
                item_id=f"{plan.plan_id}_header",
                source_type="evidence",
                title="Governed Context",
                content=header,
                priority=0.98,
                metadata={
                    "context_injection_plan_id": plan.plan_id,
                    "citation_ids": citation_ids,
                    "source_summary": plan.source_summary,
                    "auto_injected": False,
                },
            )
        )
        for context_item in plan.context_items:
            items.append(
                PromptContextItem(
                    item_id=context_item.context_item_id,
                    source_type="evidence",
                    title=f"Governed context: {context_item.source_type}",
                    content=context_item.content,
                    priority=0.9,
                    metadata={
                        "context_injection_plan_id": plan.plan_id,
                        "context_kind": context_item.kind,
                        "source_id": context_item.source_id,
                        "source_type": context_item.source_type,
                        "citation_ids": context_item.citation_ids,
                        "provenance": context_item.provenance.model_dump(),
                        "auto_injected": False,
                    },
                )
            )

    def _append_dict_item(
        self,
        items: list[PromptContextItem],
        source_type: str,
        title: str,
        value: dict[str, Any],
        *,
        priority: float,
    ) -> None:
        if not value:
            return
        items.append(
            PromptContextItem(
                source_type=source_type,  # type: ignore[arg-type]
                title=title,
                content=self._stable_repr(value),
                priority=priority,
                metadata={"generated_by": "prompt_assembly_service"},
            )
        )

    def _append_file_bundle(self, items: list[PromptContextItem], bundle: dict[str, Any]) -> None:
        raw_items = bundle.get("items", []) if isinstance(bundle.get("items", []), list) else []
        for index, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                continue
            content = str(raw.get("content") or raw.get("summary") or "")
            if not content:
                continue
            items.append(
                PromptContextItem(
                    source_type="file",
                    title=str(raw.get("title") or raw.get("path") or f"File context {index + 1}"),
                    content=content,
                    priority=float(raw.get("priority", 0.7)),
                    metadata={"path": raw.get("path"), "generated_by": "prompt_assembly_service"},
                )
            )

    def _append_project_report(self, items: list[PromptContextItem], report: dict[str, Any]) -> None:
        if not report:
            return
        summary = report.get("summary") or report.get("executive_summary") or ""
        findings = report.get("findings") if isinstance(report.get("findings"), list) else []
        text_parts = []
        if summary:
            text_parts.append("Summary: " + str(summary))
        if findings:
            text_parts.append("Findings:\n" + "\n".join("- " + self._stable_repr(item) for item in findings))
        content = "\n".join(text_parts) if text_parts else self._stable_repr(report)
        items.append(
            PromptContextItem(
                source_type="report",
                title=str(report.get("title") or "Project report"),
                content=content,
                priority=0.85,
                metadata={"generated_by": "prompt_assembly_service"},
            )
        )

    def _dict_to_block(self, title: str, value: dict[str, Any]) -> str:
        if not value:
            return ""
        return f"{title}:\n{self._stable_repr(value)}"

    def _stable_repr(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            import json

            return json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2)
        except TypeError:
            return str(value)



