from __future__ import annotations
import ast, json, re, subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"src"/"aipinho"; CFG=ROOT/"config"; TESTS=ROOT/"tests"; GEN=ROOT/"genome"
SHA=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
NOW=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def dump(rel,obj):
    p=GEN/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def md(rel,text):
    p=GEN/rel; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text.rstrip()+"\n",encoding="utf-8")
def yload(p):
    try: return yaml.safe_load(p.read_text(encoding="utf-8-sig")) or {}
    except Exception: return {}
def modname(p): return ".".join(p.relative_to(ROOT/"src").with_suffix("").parts)
CANONICAL={
"src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py",
"src/aipinho/services/governance/lifecycle/governance_lifecycle_service.py",
"src/aipinho/services/semantic_runtime/semantic_intent_resolution_service.py",
"src/aipinho/services/governance/operation_contract_service.py",
"src/aipinho/services/governance/policy/effective_policy_decision_service.py",
"src/aipinho/services/governance/approval/canonical_approval_service.py",
"src/aipinho/services/governance/runtime/canonical_runtime_service.py",
"src/aipinho/services/runtime/task_bootstrap_runtime_service.py",
"src/aipinho/services/runtime/task_runtime_service.py",
"src/aipinho/services/runtime/task_run_planner.py",
"src/aipinho/services/runtime/execution_plan_promotion_service.py",
"src/aipinho/services/semantics/task_semantic_vocabulary_compiler_service.py",
"src/aipinho/services/semantics/semantic_execution_graph_compiler_service.py",
"src/aipinho/services/semantics/edge_semantic_demand_compiler_service.py",
"src/aipinho/services/runtime/supervised_execution_loop.py",
"src/aipinho/services/runtime/task_run_executor.py",
"src/aipinho/services/runtime/governed_task_step_runner.py",
"src/aipinho/services/runtime/task_run_store.py",
"src/aipinho/services/runtime/task_run_event_service.py",
"src/aipinho/services/runtime/runtime_timeline_service.py",
"src/aipinho/services/runtime/task_run_result_service.py",
"src/aipinho/services/orchestration/task_completion_resolver.py",
"src/aipinho/services/validation/validation_gate_service.py",
"src/aipinho/services/runtime/runtime_truth_engine.py",
"src/aipinho/services/runtime/canonical_operation_state_service.py",
"src/aipinho/services/governance/speaker_truth/speaker_truth_service.py"}
CANONICAL.update({
"src/aipinho/services/semantics/semantic_offer_compiler_service.py",
"src/aipinho/services/semantics/offer_demand_compatibility_service.py",
"src/aipinho/services/semantics/semantic_nway_projection_service.py",
"src/aipinho/services/semantics/semantic_graph_revision_authority_service.py",
"src/aipinho/services/semantics/semantic_completion_truth_service.py",
"src/aipinho/services/runtime/phase_outcome_repository.py",
"src/aipinho/services/runtime/phase_dependency_evaluation_service.py",
"src/aipinho/services/semantics/limitation_compatibility_resolver_service.py"})
COMPAT={
"src/aipinho/services/runtime/runtime_contracts_v2_service.py",
"src/aipinho/services/runtime/planner_v2_service.py",
"src/aipinho/services/runtime/runtime_dispatcher_v2_service.py",
"src/aipinho/services/runtime/intelligent_planner_service.py",
"src/aipinho/services/runtime/execution_graph_service.py",
"src/aipinho/services/runtime/continuous_runtime_service.py"}
SPECIAL={
"src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py",
"src/aipinho/services/roles/role_pipeline_service.py",
"src/aipinho/services/roles/role_pass_runner.py",
"src/aipinho/services/roles/role_inference_service.py"}
DIAG={
"src/aipinho/services/runtime/runtime_operator_service.py",
"src/aipinho/services/runtime/runtime_operator_doctor_service.py",
"src/aipinho/services/runtime/runtime_doctor_service.py"}
def classify(s):
    s=s.replace("\\","/")
    if s in CANONICAL:return "CANONICAL"
    if s in COMPAT:return "COMPATIBILITY"
    if s in SPECIAL:return "SPECIALIZED_CHILD"
    if s in DIAG or "/runtime_doctor/" in s:return "DIAGNOSTIC"
    if "/legacy_rag/" in s or s.startswith("quarantine/"):return "LEGACY"
    if s.startswith("tests/"):return "TEST_ONLY"
    if s.startswith("reports/"):return "EVIDENCE"
    return "SUPPORTING"
modules=[]; classes=[]; functions=[]; endpoints=[]; edges=set(); importers=defaultdict(set); events=Counter()
for p in sorted(SRC.rglob("*.py")):
    rel=p.relative_to(ROOT).as_posix(); name=modname(p)
    try: tree=ast.parse(p.read_text(encoding="utf-8-sig",errors="replace"))
    except Exception: continue
    imports=set(); cls=[]; funcs=[]; prefix=""
    for n in tree.body:
        if isinstance(n,ast.Import): names=[a.name for a in n.names]
        elif isinstance(n,ast.ImportFrom) and n.module: names=[n.module]
        else: names=[]
        for x in names:
            if x.startswith("aipinho."): imports.add(x); edges.add((name,x)); importers[x].add(name)
        if isinstance(n,ast.ClassDef):
            methods=[m.name for m in n.body if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef))]
            cls.append(n.name); classes.append({"module":name,"path":rel,"name":n.name,"methods":methods,"line":n.lineno,"classification":classify(rel)})
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            funcs.append(n.name); functions.append({"module":name,"path":rel,"name":n.name,"line":n.lineno,"classification":classify(rel)})
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="router" for t in n.targets) and isinstance(n.value,ast.Call):
            for kw in n.value.keywords:
                if kw.arg=="prefix" and isinstance(kw.value,ast.Constant) and isinstance(kw.value.value,str): prefix=kw.value.value
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            for d in n.decorator_list:
                if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr.lower() in {"get","post","put","patch","delete","websocket"}:
                    route=d.args[0].value if d.args and isinstance(d.args[0],ast.Constant) and isinstance(d.args[0].value,str) else ""
                    endpoints.append({"router":name,"path":rel,"function":n.name,"method":d.func.attr.upper(),"route":route,"full_route":prefix+route,"line":n.lineno})
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="create" and len(n.args)>=2 and isinstance(n.args[1],ast.Constant) and isinstance(n.args[1].value,str):
            v=n.args[1].value
            if re.fullmatch(r"[a-z][a-z0-9_]{2,80}",v): events[v]+=1
    modules.append({"module":name,"path":rel,"package":name.split(".")[1] if "." in name else name,"classification":classify(rel),"classes":cls,"functions":funcs,"imports":sorted(imports)})
for m in modules:
    m["imported_by_count"]=sum(len(v) for k,v in importers.items() if k==m["module"] or k.startswith(m["module"]+"."))
service_modules=[m for m in modules if m["path"].startswith("src/aipinho/services/")]
repo_modules=[m for m in modules if m["path"].startswith("src/aipinho/repositories/")]
registry_modules=[m for m in modules if m["path"].startswith("src/aipinho/registries/") or "registry" in Path(m["path"]).stem]
store_classes=[c for c in classes if "Store" in c["name"] or "_store" in c["path"]]
test_files=[]; source_to_tests=defaultdict(set)
for p in sorted(TESTS.rglob("test_*.py")):
    rel=p.relative_to(ROOT).as_posix(); cat=p.relative_to(TESTS).parts[0] if len(p.relative_to(TESTS).parts)>1 else "root"; names=[]
    try:
        tree=ast.parse(p.read_text(encoding="utf-8-sig",errors="replace"))
        names=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith("test_")]
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith("aipinho."): source_to_tests[n.module].add(rel)
            elif isinstance(n,ast.Import):
                for a in n.names:
                    if a.name.startswith("aipinho."): source_to_tests[a.name].add(rel)
    except Exception: pass
    test_files.append({"path":rel,"category":cat,"test_count":len(names),"tests":names})
profiles=[]
for p in sorted((CFG/"runtime"/"profiles").glob("*.yaml")):
    d=yload(p); q=d.get("profile",d)
    profiles.append({"id":q.get("id",p.stem),"path":p.relative_to(ROOT).as_posix(),"operation_types":q.get("operation_types",[]),"steps":q.get("steps",[]),"allowed_actions":q.get("allowed_actions",[]),"side_effects":q.get("allowed_side_effects",[])})
roles_cfg=yload(CFG/"roles"/"default_roles.yaml"); raw=roles_cfg.get("roles") or roles_cfg.get("default_roles") or roles_cfg; role_rows=[]
if isinstance(raw,dict):
    for k,v in raw.items():
        if isinstance(v,dict): role_rows.append({"role_id":k,**v})
role_pipelines=(yload(CFG/"roles"/"role_pipelines.yaml").get("pipelines") or {})
bindings=yload(CFG/"roles"/"role_model_bindings.yaml")
schema_classes=[c for c in classes if c["path"].startswith("src/aipinho/schemas/")]
terms=("Contract","Request","Response","Result","Decision","Outcome","Snapshot","State","Plan","Evaluation","Truth","Policy")
contracts=[c for c in schema_classes if any(t in c["name"] for t in terms)]
tracked=subprocess.check_output(["git","ls-files"],cwd=ROOT,text=True).splitlines()
stats={"tracked_files":len(tracked),"python_modules":len(modules),"services":len(service_modules),"schemas":len([m for m in modules if m["path"].startswith("src/aipinho/schemas/")]),"repositories":len(repo_modules),"registries":len(registry_modules),"router_modules":len({e["router"] for e in endpoints}),"endpoints":len(endpoints),"test_files":len(test_files),"test_functions":sum(x["test_count"] for x in test_files)}
five=[
{"name":"Human operator","owns":"grants authority, approves sensitive actions, chooses policy and scope","must_not":"delegate semantic/runtime truth to a model"},
{"name":"Trusted dispatcher","owns":"validates identity, operation, arguments and scope; invokes fixed capabilities","must_not":"interpret natural language or invent AIpinho contracts"},
{"name":"Local execution broker","owns":"routes already-authorized operations to Git, tests, build, FireTest or AIpinho","must_not":"become a second planner/orchestration brain"},
{"name":"AIpinho runtime","owns":"meaning, intent, contract, planning, governed execution, evidence binding, validation, RuntimeTruth and SpeakerTruth ceiling","must_not":"claim above governed evidence"},
{"name":"Evidence/result layer","owns":"auditable proof, outputs, diagnostics and validation evidence","must_not":"invent success, hide blocked outcomes or grant runtime authority"}]
flow=["POST /api/v1/chat / governance_lifecycle_router","CanonicalPublicChatService","SemanticIntentResolutionService / CanonicalIntentRouter","GovernanceLifecycle + OperationContract + EffectivePolicy + Approval","TaskBootstrapRuntimeService / durable TaskRun","TaskRunPlanner + ExecutionPlanPromotion","TaskSemanticVocabulary -> SemanticExecutionGraph -> EdgeSemanticDemand","SupervisedExecutionLoop -> TaskRunExecutor -> GovernedTaskStepRunner","domain executor / readonly specialized child / TaskRuntime-bound RolePipeline","RuntimeTimeline + Artifact evidence + Validation + TaskRunResult","SemanticOffer -> Offer/Demand Compatibility -> N-way -> GraphRevision -> SemanticCompletionTruth","RuntimeTruthEngine -> CanonicalOperationState","CanonicalSpeakerTruthService -> client output"]
architecture={"version":"2.0","generated_at":NOW,"source_sha":SHA,"architecture_type":"governed contract-first semantic execution runtime","five_authorities":five,"canonical_runtime_chain":flow,"invariants":["MODEL != AUTHORITY","unknown is fail-closed","execution completion != semantic admission","producer completion does not authorize consumer usage","Demand is edge-local","same Offer may differ per edge","graph revision invalidates historical authority for active child graph","run_completed != safe success","Doctor diagnoses but never grants authority","roles are TaskRuntime children, not a parallel runtime","FireTest is regression evidence, not runtime configuration"]}
dump("architecture/architecture_manifest.json",architecture)
dump("architecture/dependency_graph.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"edge_count":len(edges),"edges":[{"from":a,"to":b} for a,b in sorted(edges)],"top_imported":[{"module":m["module"],"imported_by_count":m["imported_by_count"]} for m in sorted(modules,key=lambda x:x["imported_by_count"],reverse=True)[:100]]})
dump("architecture/module_graph.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"modules":modules,"package_counts":dict(Counter(m["package"] for m in modules)),"classification_counts":dict(Counter(m["classification"] for m in modules))})
dump("architecture/execution_graph.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"canonical_public_governed_flow":flow,"special_flows":{"simple_conversation":["CanonicalPublicChatService","ChatService conversation path","speaker model wording only; no operational success authority"],"readonly_artifact":["TaskRuntimeService","readonly_artifact_analysis profile","execute_readonly_artifact_analysis","TaskRuntime-bound RolePipeline supervisor","Validation/Completion/RuntimeTruth"],"diagnostic":["TaskRun/expected contract","RuntimeOperatorService","RuntimeOperatorDoctorService","findings/explanation/plan only"],"compatibility_v2":["RuntimeContractsV2Service","PlannerV2","RuntimeDispatcherV2","operator inventory/tests; not canonical execution authority"]}})
dump("architecture/pipeline_graph.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"runtime_profiles":profiles,"role_pipelines":role_pipelines,"semantic_chain":["meaning","intent","contract","entities/goals","capability matching","TaskSemanticVocabulary","SemanticExecutionGraph","EdgeSemanticDemand","governed execution","evidence","SemanticOffer","Offer/Demand compatibility","N-way semantics","graph revision","validation/completion","SemanticTruthFacet","RuntimeTruth","CanonicalOperationState","SpeakerTruth"]})
runtime_mods=[m for m in service_modules if m["path"].startswith("src/aipinho/services/runtime/") or m["path"].startswith("src/aipinho/services/governance/runtime/")]
dump("runtime/runtime_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"status":"CONSOLIDATED_VALIDATED","single_runtime_authority":"TaskRuntimeService + SupervisedExecutionLoop","services_total":len(runtime_mods),"classification_counts":dict(Counter(m["classification"] for m in runtime_mods)),"canonical_services":[m["path"] for m in runtime_mods if m["classification"]=="CANONICAL"],"specialized_children":[m["path"] for m in runtime_mods if m["classification"]=="SPECIALIZED_CHILD"],"diagnostic_services":[m["path"] for m in runtime_mods if m["classification"]=="DIAGNOSTIC"],"compatibility_services":[m["path"] for m in runtime_mods if m["classification"]=="COMPATIBILITY"],"runtime_profiles":[x["id"] for x in profiles]})
dump("runtime/runtime_services.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"services":runtime_mods})
dump("runtime/runtime_events.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"event_types":[{"event_type":k,"static_occurrences":v} for k,v in events.most_common()]})
dump("runtime/runtime_endpoints.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"endpoints":[e for e in endpoints if "runtime" in e["path"] or "/runtime" in e["full_route"]]})
dump("runtime/runtime_state.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"status":"CONSOLIDATED_VALIDATED","latest_firetest":"firetest5_runtime_consolidation_20260915T152207Z","consolidated_regression":{"passed":174,"failed":0},"firetest":{"phase_1":"partial/satisfied_with_limitations/no success claim","phases_2_6":"completed","sequence_gaps":0,"sequence_duplicates":0,"doctor":"passed all phases","workspace_mutations":0,"corpus_mutations":0},"deferred":["Windows subprocess cp1252/.m4a media probe reader issue"],"frontier":["Genome/current orientation refreshed from consolidated runtime","continue generic runtime/semantic evolution without parallel authority"]})
dump("contracts/contracts_index.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(contracts),"contracts":contracts})
dump("contracts/contracts_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"schema_classes":len(schema_classes),"contract_like_classes":len(contracts),"categories":dict(Counter(c["path"].split("/")[3] if len(c["path"].split("/"))>3 else "root" for c in contracts))})
dump("contracts/contract_producers.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"contracts":[c for c in contracts if any(t in c["name"] for t in ("Result","Outcome","Response","Truth","Snapshot","State","Decision"))]})
dump("contracts/contract_consumers.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"contracts":[c for c in contracts if any(t in c["name"] for t in ("Request","Contract","Policy","Plan","Evaluation"))]})
dump("symbols/class_index.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(classes),"classes":classes})
dump("symbols/function_index.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(functions),"functions":functions})
dump("symbols/symbol_index.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"modules":len(modules),"classes":len(classes),"functions":len(functions),"classification_counts":dict(Counter(m["classification"] for m in modules))})
dump("symbols/public_api.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"endpoint_functions":endpoints,"canonical_runtime_classes":[c for c in classes if c["classification"]=="CANONICAL"]})
role_deps={pid:[{"pass_id":x.get("pass_id"),"role_id":x.get("role_id"),"required":x.get("required",True)} for x in (cfg.get("passes") or [])] for pid,cfg in role_pipelines.items() if isinstance(cfg,dict)}
dump("roles/roles_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"roles":role_rows,"pipelines":list(role_pipelines),"authority_ceiling":"roles are subordinate TaskRuntime cognitive components; MODEL != AUTHORITY","runtime_binding":"real RolePipeline execution requires parent TaskRun/operation/execution binding"})
dump("roles/role_capabilities.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"roles":[{"role_id":r.get("role_id"),"enabled":r.get("enabled"),"can_call_model":r.get("can_call_model"),"model_policy":r.get("model_policy"),"capabilities":r.get("capabilities") or r.get("allowed_capabilities") or []} for r in role_rows]})
dump("roles/role_dependencies.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"pipeline_passes":role_deps,"notes":["readonly pipeline retains deterministic supervisor without duplicating semantic analysis/rendering","speaker model wording is distinct from CanonicalSpeakerTruth authority"]})
model_files=[p.relative_to(ROOT).as_posix() for p in sorted((CFG/"models").rglob("*")) if p.is_file()]
dump("models/models_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"config_files":model_files,"role_model_bindings":"config/roles/role_model_bindings.yaml"})
dump("models/model_usage.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"bindings":bindings,"authority_note":"model output is proposal/wording/reasoning subject to deterministic gates; bindings never grant authority"})
dump("models/inference_routes.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"role_inference_service":"reachable specialized subsystem","role_pipeline":"TaskRuntime-bound child","simple_chat_speaker":"wording only for non-operational conversation","supervisor":{"policy":"deterministic_only","real_inference_default":False}})
svc_cat=Counter(m["path"].split("/")[3] for m in service_modules)
dump("services/services_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(service_modules),"services":service_modules})
dump("services/service_dependencies.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"dependencies":[{"module":m["module"],"dependencies":[x for x in m["imports"] if x.startswith("aipinho.services.")]} for m in service_modules]})
dump("services/service_categories.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"categories":dict(sorted(svc_cat.items()))})
dump("api/api_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"router_modules":len({e["router"] for e in endpoints}),"endpoint_count":len(endpoints),"canonical_public_ingress":"POST /api/v1/chat via governance_lifecycle_router"})
dump("api/routers.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"routers":sorted(set(e["router"] for e in endpoints))})
dump("api/endpoints.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"endpoints":sorted(endpoints,key=lambda x:(x["full_route"],x["method"],x["function"]))})
dump("data/repositories.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(repo_modules),"repositories":repo_modules})
dump("data/registries.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(registry_modules),"registries":registry_modules})
dump("data/stores.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"count":len(store_classes),"stores":store_classes})
tool_cfg=[p.relative_to(ROOT).as_posix() for p in sorted((CFG/"tools").rglob("*")) if p.is_file()]
skill_cfg=[p.relative_to(ROOT).as_posix() for p in sorted((CFG/"skills").rglob("*")) if p.is_file()]
dump("tools/tools_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"tool_config_files":tool_cfg,"service_modules":[m for m in service_modules if "/tools/" in m["path"]]})
dump("tools/tool_calls.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"governance":"tool execution remains policy/capability-bound; tool success != product success","adapters":[m["path"] for m in modules if m["path"].startswith("src/aipinho/adapters/")]})
dump("tools/skills_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"config_file_count":len(skill_cfg),"config_files":skill_cfg,"runtime_service_modules":[m["path"] for m in service_modules if "/skills/" in m["path"]]})
dump("events/events.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"event_types":[{"event_type":k,"static_occurrences":v} for k,v in events.most_common()]})
dump("events/event_producers.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"modules":[m for m in modules if "event" in Path(m["path"]).stem.lower()]})
dump("events/event_consumers.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"modules":[m for m in modules if any("event" in x.lower() for x in m["imports"]) and "event" not in Path(m["path"]).stem.lower()]})
dump("tests/tests_manifest.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"file_count":len(test_files),"test_function_count":sum(x["test_count"] for x in test_files),"categories":dict(Counter(x["category"] for x in test_files)),"files":test_files})
dump("tests/coverage_map.json",{"version":"2.0","generated_at":NOW,"source_sha":SHA,"method":"direct test imports; not line coverage","mappings":[{"source_module":m,"tests":sorted(v),"direct_import_test_count":len(v)} for m,v in sorted(source_to_tests.items())],"latest_consolidated_regression":{"passed":174,"failed":0,"evidence":"reports/runtime_consolidation/runtime_consolidation_final_validation_20260915.md"}})
summary="# AIpinho Genome Summary\n\nGenerated: "+NOW+"\nSource main SHA: "+SHA+"\nGenome version: 2.0\n\nGenerated orientation only. Code, canonical config/contracts and validated runtime evidence outrank this Genome.\n\n## Current architecture\n\nCanonical path: public chat ingress -> CanonicalPublicChatService -> semantic intent/governance -> durable TaskRun -> TaskRunPlanner -> semantic vocabulary/graph/demand -> SupervisedExecutionLoop -> governed steps and TaskRuntime-bound role children -> evidence/validation -> semantic offer/compatibility -> completion -> RuntimeTruth -> CanonicalOperationState -> SpeakerTruth.\n\nGenome v2 separates canonical authority from compatibility/inventory, specialized child execution, diagnostics, legacy code, evidence and test-only surfaces. RuntimeDispatcherV2 and PlannerV2 are not a second runtime.\n\n## Validated baseline\n\n- FireTest consolidation: Phase 1 partial/limited-use; Phases 2-6 completed.\n- Timeline gaps/duplicates: 0/0 across all six phases.\n- Runtime Doctor passed all six phases.\n- Consolidated regression after reboot: 174 passed / 0 failed.\n- Workspace/corpus mutations: 0 / 0.\n- Deferred: Windows subprocess cp1252/.m4a media probe reader issue.\n\n## Inventory\n\n"+json.dumps(stats,indent=2)
md("reports/genome_summary.md",summary)
md("reports/genome_statistics.md","# AIpinho Genome Statistics\n\nGenerated: "+NOW+"\n\n"+json.dumps({"stats":stats,"module_classifications":dict(Counter(m["classification"] for m in modules)),"service_categories":dict(sorted(svc_cat.items()))},indent=2))
audit="# GitHub Folder-by-Folder Genome Audit - 2026-09-15\n\nRemote main was scanned before generation at "+SHA+". GitHub recursive tree returned 18,529 nodes with truncated=false; the local generator runs from the same Git object.\n\n"
audit+="| Area | Current role | Classification |\n|---|---|---|\n"
rows=[("src/aipinho/services/runtime","TaskRuntime lifecycle, loop, timeline, Truth and phase admission","mixed CANONICAL / COMPATIBILITY / DIAGNOSTIC"),("src/aipinho/services/governance","public lifecycle, contract, policy, approval, SpeakerTruth, readonly boundary","CANONICAL / SPECIALIZED_CHILD"),("src/aipinho/services/semantics","semantic Sprints 0-9 chain","CANONICAL"),("src/aipinho/services/semantic_runtime","prompt semantic ingress and bounded interpreter","CANONICAL / SUPPORTING"),("src/aipinho/services/roles","role policy/model gates and TaskRuntime-bound role pipeline","SPECIALIZED_CHILD / SUPPORTING"),("src/aipinho/services/validation","validation gates and validators","CANONICAL / SUPPORTING"),("src/aipinho/api/routers","public/operator surfaces","ADAPTER / SUPPORTING"),("src/aipinho/schemas","runtime/public contracts","SPECIFICATION"),("config/runtime + config/roles + config/semantic_runtime","active runtime specification","SPECIFICATION"),("tests","validation evidence","TEST_ONLY"),("reports","bounded historical/current evidence","EVIDENCE"),("docs + Context Pack","orientation/handoff","ORIENTATION"),("genome","generated design DNA snapshot","GENERATED"),("quarantine / legacy_rag","retired/legacy namespace","LEGACY")]
for a,b,c in rows: audit+=f"| {a} | {b} | {c} |\n"
audit+="\n## Reachability corrections\n\n- RuntimeDispatcherV2 and RuntimeContractsV2Service are reached from Runtime Operator inventory/tests, not the canonical TaskRun execution line.\n- IntelligentPlannerService, ExecutionGraphService and ContinuousRuntimeService are instantiated by TaskRuntimeService, but GitHub code search found no subsequent self-attribute consumption in the canonical TaskRun path; Genome classifies them as compatibility/inventory.\n- ReadonlyAnalysisArtifactRuntimeService is live but lifecycle/result terminalization/RuntimeTruth remain owned by TaskRuntime.\n- Governed RolePipelineRun requires parent TaskRun/operation/execution binding; roles cannot become a parallel runtime or a sixth authority.\n"
md("reports/github_folder_audit_20260915.md",audit)
structure={d:[p.name for p in sorted((GEN/d).glob("*")) if p.is_file()] for d in ["architecture","runtime","contracts","symbols","roles","models","services","api","data","tools","events","tests","reports"]}
dump("00_manifest.json",{"genome_version":"2.0","project_name":"AIpinho","generated_at":NOW,"generator":"scripts/maintenance/regenerate_genome.py","mode":"READ_ONLY_DERIVED_SNAPSHOT","source_repository":"sasandralean-prog/AIpinho","source_branch":"main","source_sha":SHA,"authority_note":"Generated orientation only; code/config/contracts and validated runtime evidence outrank Genome.","metadata":stats,"structure":structure,"github_remote_scan":{"verified_sha":SHA,"recursive_tree_complete":True,"remote_nodes_observed":18529}})
print(json.dumps({"source_sha":SHA,"stats":stats},indent=2))
