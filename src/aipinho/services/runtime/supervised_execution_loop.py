from __future__ import annotations
import time
from datetime import datetime
from aipinho.services.session.session_store import utc_now
from aipinho.services.runtime.task_run_audit_service import TaskRunAuditService
from aipinho.services.runtime.task_run_context_service import TaskRunContextService
from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_executor import TaskRunExecutor
from aipinho.services.runtime.task_run_guard import TaskRunGuard
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_result_service import TaskRunResultService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_block_cause_service import TaskBlockCauseService
from aipinho.services.runtime.task_run_trace_service import TaskRunTraceService
from aipinho.services.runtime.execution_graph_service import ExecutionGraphService
from aipinho.services.runtime.workflow_runtime_service import WorkflowRuntimeService
from aipinho.services.runtime.workspace_context_service import ExecutionContextService
from aipinho.services.orchestration.task_completion_resolver import TaskCompletionResolver

class SupervisedExecutionLoop:
    def __init__(self, store=None, lifecycle=None, guard=None, events=None, audit=None, executor=None, contexts=None, results=None):
        self.store=store or TaskRunStore(); self.lifecycle=lifecycle or TaskRunLifecycleService(); self.guard=guard or TaskRunGuard(lifecycle=self.lifecycle)
        self.events=events or TaskRunEventService(self.store); self.audit=audit or TaskRunAuditService(self.store); self.executor=executor or TaskRunExecutor(); self.contexts=contexts or TaskRunContextService(); self.results=results or TaskRunResultService(self.store)
        self.block_causes=TaskBlockCauseService(); self.trace_service=TaskRunTraceService(); self.completion=TaskCompletionResolver()
        self.graphs=ExecutionGraphService()
        self.workflows=WorkflowRuntimeService()
        self.execution_contexts=ExecutionContextService()

    def run(self, run_id):
        run=self.store.get_run(run_id)
        if run is None: raise ValueError("task_run_not_found")
        existing=self.store.get_result(run_id)
        if self.lifecycle.is_terminal(run.status) or run.status=="running": return run,existing
        timeline_reasons = self._timeline_bootstrap_reasons(run_id)
        if timeline_reasons:
            run.blocked_reasons=list(dict.fromkeys([*run.blocked_reasons,*timeline_reasons])); self.lifecycle.transition(run,"blocked")
            self._record_block(run,"TaskRun blocked because the runtime timeline is incomplete."); self.audit.record(run_id=run_id,action="start",status="blocked",reason=",".join(timeline_reasons))
            self.store.update_run(run); self.store.save_trace(run_id,run.trace); result=self.results.build(run,self.contexts.build(run),events_count=len(self.events.list(run_id))); self.store.save_result(run_id,result); return run,result
        initial=self.guard.check_run(run); run.trace.extend(initial.trace)
        if not initial.allowed:
            run.blocked_reasons=list(dict.fromkeys([*run.blocked_reasons,*initial.blocked_reasons])); self.lifecycle.transition(run,"blocked")
            self._record_block(run,"TaskRun blocked by initial guard."); self.audit.record(run_id=run_id,action="start",status="blocked",reason=",".join(initial.blocked_reasons))
            self.store.update_run(run); self.store.save_trace(run_id,run.trace); result=self.results.build(run,self.contexts.build(run),events_count=len(self.events.list(run_id))); self.store.save_result(run_id,result); return run,result
        if run.status=="created": self.lifecycle.transition(run,"queued"); self.events.create(run_id,"run_queued","queued","TaskRun queued for explicit synchronous execution.")
        if run.approval_id:
            self.events.create(run_id,"ExecutionPlanApproved","approved","ExecutionPlan approval observed before execution.",metadata={"approval_id":run.approval_id,"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None})
        self.lifecycle.transition(run,"running"); self.events.create(run_id,"ExecutionStarted","running","Canonical ExecutionPlan execution started.",metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None}); self.events.create(run_id,"run_started","running","Supervised read-only execution started."); self.audit.record(run_id=run_id,action="start",status="allowed",reason="explicit_start"); self.store.update_run(run)
        context=self.contexts.build(run); started=time.monotonic(); partial=False; terminal=None
        for index,step in enumerate(run.plan.steps):
            latest=self.store.get_run(run_id)
            if latest and latest.cancellation_requested: run.cancellation_requested=True; run.cancellation_reason=latest.cancellation_reason
            decision=self.guard.check_step(run,step,step_index=index,elapsed_seconds=time.monotonic()-started); run.trace.extend(decision.trace)
            if not decision.allowed:
                if "cancellation_requested" in decision.blocked_reasons:
                    step.status="cancelled"; step.finished_at=utc_now(); terminal="cancelled"; self.events.create(run_id,"step_cancelled","cancelled","Step cancelled before execution.",step_id=step.step_id)
                else:
                    step.status="blocked"; step.violations.extend(decision.blocked_reasons); run.blocked_reasons=list(dict.fromkeys([*run.blocked_reasons,*decision.blocked_reasons])); step.finished_at=utc_now(); terminal="blocked"; self.events.create(run_id,"step_blocked","blocked","Step blocked by TaskRunGuard.",step_id=step.step_id,metadata={"reasons":decision.blocked_reasons}); self.audit.record(run_id=run_id,step_id=step.step_id,action=step.action,status="blocked",reason=",".join(decision.blocked_reasons))
                break
            deps_allowed, dependency_reasons = self.workflows.can_start_phase(run.workflow, step.step_id)
            if not deps_allowed:
                step.status="blocked"; step.violations.extend(dependency_reasons); run.blocked_reasons=list(dict.fromkeys([*run.blocked_reasons,*dependency_reasons])); step.finished_at=utc_now(); terminal="blocked"; self.events.create(run_id,"step_blocked","blocked","Step blocked by Workflow dependency runtime.",step_id=step.step_id,metadata={"reasons":dependency_reasons}); self.audit.record(run_id=run_id,step_id=step.step_id,action=step.action,status="blocked",reason=",".join(dependency_reasons)); self.store.update_run(run); break
            phase = self.workflows.phase_for_step(run.workflow, step.step_id) if run.workflow else None
            run.current_step_id=step.step_id; step.status="running"; step.started_at=utc_now(); run.execution_graph=self.graphs.mark_step_started(run.execution_graph, step.step_id); run.revision+=1; self.events.create(run_id,"StepStarted","running",f"Canonical step {step.step_type} started.",step_id=step.step_id,metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None,"action":step.action}); start_event=self.events.create(run_id,"step_started","running",f"Step {step.step_type} started.",step_id=step.step_id,metadata={"workflow_id":run.workflow.workflow_id if run.workflow else None,"phase_id":phase.phase_id if phase else None}); run.workflow=self.workflows.start_phase_for_step(run.workflow, step.step_id, event_id=start_event.event_id); self.store.update_run(run)
            run.execution_context=self.execution_contexts.record_phase(run,phase_id=phase.phase_id if phase else None,status="running",event_id=start_event.event_id); self.store.update_run(run)
            outcome=self.executor.execute_step(run,step,context); step.status=outcome.status; step.output_summary=self.store.sanitize(outcome.summary); step.warnings=list(dict.fromkeys(outcome.warnings)); step.violations=list(dict.fromkeys(outcome.violations)); step.finished_at=utc_now()
            run.execution_graph=self.graphs.mark_step_finished(run.execution_graph, step.step_id, status=outcome.status, output_summary=step.output_summary, warnings=step.warnings, violations=step.violations)
            if outcome.status in {"completed", "partial"} and step.output_summary:
                context.outputs.setdefault(step.action, step.output_summary)
                context.outputs.setdefault(step.step_type, step.output_summary)
            context.limitations.extend(outcome.limitations); context.blocked_items.extend(outcome.blocked_items); context.warnings.extend(outcome.warnings)
            if outcome.status == "blocked":
                run.blocked_reasons=list(dict.fromkeys([*run.blocked_reasons,*outcome.violations,*outcome.blocked_items]))
            event_type={"completed":"step_completed","partial":"step_partial","failed":"step_failed","blocked":"step_blocked","cancelled":"step_cancelled"}.get(outcome.status,"step_failed")
            self.events.create(run_id,"StepFinished",outcome.status,f"Canonical step {step.step_type} finished.",step_id=step.step_id,metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None,"action":step.action,"duration_ms":self._duration_ms(step.started_at,step.finished_at)}); finish_event=self.events.create(run_id,event_type,outcome.status,f"Step {step.step_type} finished with status {outcome.status}.",step_id=step.step_id,metadata={"warnings":outcome.warnings,"violations":outcome.violations,"duration_ms":self._duration_ms(step.started_at,step.finished_at),"step_type":step.step_type,"action":step.action,"workflow_id":run.workflow.workflow_id if run.workflow else None}); run.workflow=self.workflows.finish_phase_for_step(run.workflow,step.step_id,status=outcome.status,event_id=finish_event.event_id,validation_ref=finish_event.event_id,violations=outcome.violations); run.execution_context=self.execution_contexts.record_phase(run,phase_id=phase.phase_id if phase else None,status=outcome.status,event_id=finish_event.event_id); self.audit.record(run_id=run_id,step_id=step.step_id,action=step.action,status=outcome.status,reason="step_finished")
            run.current_step_id=None; run.revision+=1; self.store.update_run(run)
            if outcome.status=="partial": partial=True
            if outcome.status in {"failed","blocked"} and step.required: terminal="blocked" if outcome.status=="blocked" else "failed"; break
        if terminal is None:
            terminal="partial" if partial or context.limitations or context.blocked_items else "completed"
        completion=self.completion.resolve(run,context,proposed_status=terminal)
        context.outputs["_completion"]=completion
        context.limitations.extend(completion.limitations)
        context.warnings.extend(completion.warnings)
        if terminal=="completed" and completion.status!="completed":
            terminal=completion.status
        self.events.create(run_id,"ValidationStarted","validating","Validation phase started from execution outputs.",metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None}); self.events.create(run_id,"ValidationFinished",completion.status,"Validation phase finished.",metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None,"completion_status":completion.status}); self.events.create(run_id,"ArtifactsCreated","observed","Artifact expectations reconciled for execution.",metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None,"artifact_expectations":run.plan.canonical_execution_plan.artifact_expectations if run.plan.canonical_execution_plan else []}); self.events.create(run_id,"CompletionGenerated",completion.status,"Completion generated from timeline and validation.",metadata=completion.model_dump()); self.events.create(run_id,"task_completion_evaluated",completion.status,"Task completion contract evaluated.",metadata=completion.model_dump())
        if terminal=="cancelled":
            run.execution_graph=self.graphs.mark_cancelled(run.execution_graph, run.cancellation_reason or "task_cancelled")
        self.lifecycle.transition(run,terminal); final_event={"completed":"run_completed","partial":"run_partial","failed":"run_failed","cancelled":"run_cancelled","blocked":"run_blocked"}[terminal]
        if terminal == "blocked":
            self._record_block(run,"TaskRun finished blocked by a governed runtime decision.")
        else:
            self.events.create(run_id,"SpeakerTruthGenerated",terminal,"Speaker Truth state can be derived from timeline, validation, artifacts and completion.",metadata={"execution_id":run.plan.canonical_execution_plan.execution_id if run.plan.canonical_execution_plan else None,"terminal":terminal}); self.events.create(run_id,final_event,terminal,f"TaskRun finished with status {terminal}.")
        self.audit.record(run_id=run_id,action="finish",status=terminal,reason="supervised_loop_finished")
        run.current_step_id=None; self.store.update_run(run); self.store.save_trace(run_id,run.trace); result=self.results.build(run,context,events_count=len(self.events.list(run_id))); self.store.save_result(run_id,result); return run,result

    def status(self): return {"status":"ok","service":"supervised_execution_loop","background_execution":False,"parallel_runs":False,"write_enabled":False,"patch_enabled":False,"shell_enabled":False}

    def _duration_ms(self, start: str | None, finish: str | None) -> int | None:
        if not start or not finish:
            return None
        try:
            start_dt=datetime.fromisoformat(start.replace("Z","+00:00"))
            finish_dt=datetime.fromisoformat(finish.replace("Z","+00:00"))
        except Exception:
            return None
        return max(0,int((finish_dt-start_dt).total_seconds()*1000))

    def _record_block(self, run, message):
        cause=self.block_causes.build(run,run.blocked_reasons)
        run.block_cause=cause
        run.trace.append(self.trace_service.item("task_blocked","blocked",cause.block_reason_code,source="services/runtime/supervised_execution_loop.py",data={"block_id":cause.block_id,"blocked_stage":cause.blocked_stage,"safe_alternatives":cause.safe_alternatives}))
        policy_event=self.events.create(run.run_id,"policy_decision","blocked","A runtime policy decision blocked the task.",metadata={"block_cause":cause.model_dump()})
        event=self.events.create(run.run_id,"task_blocked","blocked",message,metadata={"block_cause":cause.model_dump(),"policy_event_id":policy_event.event_id})
        cause.event_id=event.event_id
        run.block_cause=cause
        self.events.create(run.run_id,"run_blocked","blocked",message,metadata={"block_id":cause.block_id,"task_blocked_event_id":event.event_id})

    def _timeline_bootstrap_reasons(self, run_id):
        events=self.events.list(run_id)
        reasons=[]
        if not events:
            reasons.append("timeline_events_missing")
            return reasons
        sequences=[event.sequence for event in events]
        if sequences != list(range(1,len(events)+1)):
            reasons.append("event_sequence_not_contiguous")
        event_types=[event.type for event in events]
        if "run_created" not in event_types:
            reasons.append("timeline_missing_run_created")
        if "task_bootstrap_created" not in event_types:
            reasons.append("timeline_missing_task_bootstrap_created")
        return list(dict.fromkeys(reasons))
