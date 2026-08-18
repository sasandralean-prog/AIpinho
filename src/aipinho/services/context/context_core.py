from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.schemas.context.contracts import *
from aipinho.services.events.event_core import EventContractRegistryService, redact_payload
from aipinho.utils.yaml_loader import load_yaml_file

SECRET=[re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+",re.I),re.compile(r"sk-[A-Za-z0-9_-]{12,}"),re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----",re.I),re.compile(r"password\s*[:=]\s*\S+",re.I)]
INJECT=("ignore previous","ignore all previous","bypass policy","disable safety","system prompt")
CONTEXTUAL={"curated_memory","rag_chunk","vector_rag_hit","artifact_record","artifact_manifest","visual_evidence","ocr_text_block","file_summary","project_analysis"}
def dump(x): return x.model_dump() if hasattr(x,'model_dump') else x.dict()
def h(text:str)->str: return hashlib.sha256(text.encode('utf-8')).hexdigest()
def read_json(path:Path,default): return json.loads(path.read_text(encoding='utf-8')) if path.exists() and path.stat().st_size else default
def write_json(path:Path,payload): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(payload,indent=2,ensure_ascii=True),encoding='utf-8')
def source_key(s): return 'missing' if s is None else f"{s.source_type}:{s.source_id}:{s.path or ''}:{s.uri or ''}"

class ContextPurposePolicyService:
    def __init__(self,path:Path|None=None): self.path=path or PATHS.config_root/'context'/'context_purpose_policy.yaml'
    def data(self): return load_yaml_file(self.path,root=PATHS.project_root)
    def purposes(self): return self.data().get('purposes',{})
    def known(self,purpose): return purpose in self.purposes()
    def policy(self,purpose):
        if not self.known(purpose): raise ValueError('unknown_purpose')
        return self.purposes()[purpose]
    def allowed_layers(self,purpose): return set(self.policy(purpose).get('allowed_layers',[]))
    def required_citation_layers(self,purpose): return set(self.policy(purpose).get('required_citations',[]))
    def blocked_source_types(self,purpose): return set(self.policy(purpose).get('blocked_source_types',[]))
    def max_budget(self,purpose,override=None): return int(override or self.policy(purpose).get('max_budget_chars',8000))
    def status(self): return {'status':'ok','purposes':sorted(self.purposes().keys())}

class ContextLayerResolver:
    def __init__(self,path:Path|None=None): self.path=path or PATHS.config_root/'context'/'context_layer_policy.yaml'
    def layers(self): return load_yaml_file(self.path,root=PATHS.project_root).get('layers',{})
    def known(self,layer): return layer in self.layers()
    def enabled(self,layer): return bool(self.layers().get(layer,{}).get('enabled',False))
    def resolve(self,purpose):
        allowed=ContextPurposePolicyService().allowed_layers(purpose)
        return [layer for layer in self.layers() if layer in allowed and self.enabled(layer)]

class ContextRequestBuilder:
    def build(self,purpose,current_message=None,scope=None): return ContextRequest(purpose=purpose,current_message=current_message,scope=scope or ContextScope())
class ContextScopeResolver:
    def resolve(self,request): return request.scope or ContextScope()
class ContextCandidateCollector:
    def collect(self,request):
        items=list(request.candidates)
        if request.current_message:
            items.insert(0,ContextCandidate(layer='current_message',source_type='current_request',source_ref=ContextSourceRef(source_type='current_request',source_id=request.request_id),summary='Mensagem atual do usuario.',content=request.current_message,priority=10,trust_level='verified'))
        return items
class ContextFreshnessService:
    def evaluate(self,c):
        if c.freshness.status=='expired': return 'rejected',['expired_source']
        if c.freshness.status=='superseded': return 'rejected',['superseded_source']
        if c.freshness.status=='stale': return 'degraded',['stale_source']
        return 'fresh',[]
class ContextSensitivityFilter:
    def scan(self,text):
        reasons=[]; redacted=text
        for pat in SECRET:
            if pat.search(redacted): reasons.append('secret_detected'); redacted=pat.sub('[REDACTED_SECRET]',redacted)
        return not reasons,redacted,reasons
class ContextPromptInjectionGuard:
    def inspect(self,text):
        low=text.lower(); return [ContextWarning(code='prompt_injection_suspected',message=p) for p in INJECT if p in low]
class ContextSourceTrustService:
    def trust(self,c): return c.trust_level or 'candidate'
class ContextEvidenceValidator:
    def validate(self,purpose,c):
        pp=ContextPurposePolicyService(); needs=c.layer in pp.required_citation_layers(purpose) or c.source_type in CONTEXTUAL
        if needs and not c.citations and not c.evidence_refs: return False,['missing_citation_or_evidence']
        if c.source_type=='ocr_text_block' and float(c.metadata.get('confidence') or 0)<0.5: return False,['ocr_confidence_too_low']
        return True,[]
class CitationMapBuilder:
    def build(self,items):
        out={}
        for item in items:
            for cit in item.citations: out[cit.citation_id]=cit
        return out
class ChunkHashService:
    def hash(self,text): return h(text)
class ChunkDedupeService:
    def dedupe(self,candidates):
        seen_h=set(); seen_s=set(); kept=[]; dup={}
        for c in candidates:
            ch=h(c.content or c.summary); sk=source_key(c.source_ref)
            if ch in seen_h or sk in seen_s: dup[c.candidate_id]=['duplicate_content_or_source']
            else: seen_h.add(ch); seen_s.add(sk); kept.append(c)
        return kept,dup
class ContextBudgetManager:
    def policy_result(self,purpose,override=None): return ContextBudgetPolicyResult(purpose=purpose,max_chars=ContextPurposePolicyService().max_budget(purpose,override))
    def apply(self,candidates,purpose,override=None):
        maxc=ContextPurposePolicyService().max_budget(purpose,override); used=0; out={}; trunc=set()
        for c in sorted(candidates,key=lambda x:x.priority,reverse=True):
            req=len(c.content or c.summary); rem=max(0,maxc-used); adm=req if req<=rem else (rem if c.priority>=8 and rem>0 else 0)
            if adm<req: trunc.add(c.candidate_id)
            used+=adm; out[c.candidate_id]=ContextBudgetResult(status='truncated' if adm<req else 'within_budget',requested_chars=req,admitted_chars=adm,truncated_chars=max(0,req-adm),max_chars=maxc)
        return out,trunc
class ContextSourceAdmissionService:
    def validate_source(self,purpose,c):
        reasons=[]; pp=ContextPurposePolicyService(); lr=ContextLayerResolver()
        if c.source_ref is None: return ['missing_source_ref']
        if c.source_type in pp.blocked_source_types(purpose): reasons.append('source_type_blocked_for_purpose')
        if c.source_type in {'raw_prompt','raw_model_output','raw_log'}: reasons.append('raw_context_blocked')
        if c.source_type=='sanitized_raw_ref' and purpose!='debugger_analysis': reasons.append('sanitized_raw_ref_debugger_only')
        if c.source_type=='legacy_vectorstore': reasons.append('legacy_vectorstore_blocked')
        if c.source_type=='direct_workspace_path' or (c.source_ref.path and ':\\' in c.source_ref.path and c.source_type in {'artifact_record','artifact_manifest'}): reasons.append('direct_workspace_path_blocked')
        if not lr.known(c.layer): reasons.append('unknown_layer')
        elif c.layer not in pp.allowed_layers(purpose): reasons.append('layer_not_allowed_for_purpose')
        if c.source_type=='event_summary' and not EventContractRegistryService().get(c.source_ref.source_id): reasons.append('unknown_event_contract')
        return reasons
class ContextAdmissionServiceV2:
    def admit(self,request,candidates):
        pp=ContextPurposePolicyService()
        if not pp.known(request.purpose): return [ContextAdmissionDecision(candidate_id=c.candidate_id,status='rejected',reason_codes=['unknown_purpose'],human_reason='Purpose desconhecido.',blocked_reasons=['unknown_purpose']) for c in candidates]
        kept,dups=ChunkDedupeService().dedupe(candidates); budgets,trunc=ContextBudgetManager().apply(kept,request.purpose,request.max_budget_chars); decisions=[]
        for cid,reasons in dups.items(): decisions.append(ContextAdmissionDecision(candidate_id=cid,status='deduplicated',reason_codes=reasons,human_reason='Contexto duplicado.',blocked_reasons=reasons))
        for c in kept:
            reasons=ContextSourceAdmissionService().validate_source(request.purpose,c); fresh,fr=ContextFreshnessService().evaluate(c); evok,evr=ContextEvidenceValidator().validate(request.purpose,c); ok,red,sr=ContextSensitivityFilter().scan(c.content or c.summary); warns=ContextPromptInjectionGuard().inspect(c.content or c.summary); c.content=red
            if not ok: reasons+=sr
            if not evok: reasons+=evr
            if fresh=='rejected': reasons+=fr
            b=budgets.get(c.candidate_id)
            budget_truncated = bool(b and b.status=='truncated')
            if reasons: status='rejected'
            elif budget_truncated: status='truncated'
            elif warns or fresh=='degraded' or c.trust_level=='candidate': status='degraded' if c.trust_level=='candidate' else 'admitted_with_warnings'; reasons+=fr
            else: status='admitted'
            decisions.append(ContextAdmissionDecision(candidate_id=c.candidate_id,status=status,reason_codes=reasons,human_reason='Admitido pelo Context Kernel.' if status in {'admitted','admitted_with_warnings','truncated','degraded'} else 'Contexto recusado pelo Context Kernel.',policy_refs=['config/context/context_admission_policy.yaml'],budget_result=b,warnings=warns,blocked_reasons=reasons if status=='rejected' else []))
        return decisions


class ContextBundleRepository:
    def __init__(self,root:Path|None=None): self.root=root or PATHS.project_root/'data'/'runtime'/'context'/'bundles'
    def save(self,bundle): self.root.mkdir(parents=True,exist_ok=True); write_json(self.root/f'{bundle.bundle_id}.json',dump(bundle)); return bundle
    def get(self,bundle_id):
        path=self.root/f'{bundle_id}.json'
        return ContextBundle(**json.loads(path.read_text(encoding='utf-8'))) if path.exists() else None
class ContextTraceRepository:
    def __init__(self,root:Path|None=None): self.root=root or PATHS.project_root/'data'/'runtime'/'context'/'traces'
    def save(self,trace): self.root.mkdir(parents=True,exist_ok=True); write_json(self.root/f'{trace.trace_id}.json',dump(trace)); return trace
    def get(self,trace_id):
        path=self.root/f'{trace_id}.json'
        return ContextTrace(**json.loads(path.read_text(encoding='utf-8'))) if path.exists() else None
class ContextCacheRepository:
    def __init__(self,path:Path|None=None): self.path=path or PATHS.project_root/'data'/'runtime'/'context'/'cache'/'entries.json'
    def list(self): return [ContextCacheEntry(**x) for x in read_json(self.path,[])]
    def save(self,entry):
        items=[x for x in self.list() if x.key!=entry.key]; items.append(entry); write_json(self.path,[dump(x) for x in items]); return entry
    def get(self,key): return next((x for x in self.list() if x.key==key),None)
    def clear(self): write_json(self.path,[])
class ContextCacheKeyBuilder:
    def key(self,request,candidates):
        sh=h(json.dumps(dump(request.scope),sort_keys=True)); semantic=[{'layer':c.layer,'source_type':c.source_type,'source_ref':dump(c.source_ref) if c.source_ref else None,'summary':c.summary,'content_hash':h(c.content or c.summary),'priority':c.priority,'trust_level':c.trust_level,'freshness':c.freshness.status} for c in candidates]; ch=h(json.dumps(semantic,sort_keys=True)); key=h(f'{request.purpose}:{sh}:{ch}:1')
        return ContextCacheKey(key=key,purpose=request.purpose,scope_hash=sh,candidates_hash=ch)
class ContextCacheService:
    def __init__(self): self.repo=ContextCacheRepository()
    def status(self): return ContextCacheStatus(status='ok',enabled=True,entries=len(self.repo.list())).model_dump()
    def get_bundle(self,request,candidates):
        entry=self.repo.get(ContextCacheKeyBuilder().key(request,candidates).key)
        bundle=ContextBundleRepository().get(entry.bundle_id) if entry else None
        if bundle: bundle.metadata.cache_used=True
        return bundle
    def remember(self,request,candidates,bundle):
        key=ContextCacheKeyBuilder().key(request,candidates); hashes={source_key(c.source_ref):c.source_ref.source_hash or h(c.content or c.summary) for c in candidates if c.source_ref}
        self.repo.save(ContextCacheEntry(key=key.key,bundle_id=bundle.bundle_id,source_hashes=hashes))
    def invalidate(self,invalidation): self.repo.clear(); return {'status':'ok','invalidated':True,'reason':invalidation.reason}
class ContextBundleBuilder:
    def build(self,request,candidates,decisions):
        by={d.candidate_id:d for d in decisions}; items=[]; rejs=[]; warns=[]; risks=[]
        for c in candidates:
            d=by.get(c.candidate_id)
            if not d: continue
            if d.status in {'admitted','admitted_with_warnings','truncated','degraded'} and c.source_ref:
                content=c.content or c.summary
                if d.budget_result and d.budget_result.status=='truncated': content=content[:d.budget_result.admitted_chars]
                item=ContextItem(layer=c.layer,source_type=c.source_type,source_ref=c.source_ref,summary=c.summary,content=content,content_hash=h(content),citations=c.citations,evidence_refs=c.evidence_refs,trust_level=c.trust_level,freshness=c.freshness,budget_chars=len(content),injection_slot=c.layer,warnings=d.warnings)
                items.append(item); warns+=d.warnings
                if d.status!='admitted': risks.append(d.status)
            else:
                code=d.reason_codes[0] if d and d.reason_codes else (d.status if d else 'unknown')
                rejs.append(ContextRejectionReason(candidate_id=c.candidate_id,code=code,human_reason=d.human_reason if d else 'Sem decisao.'))
                if code in {'secret_detected','raw_context_blocked'}: risks.append(code)
        maxc=ContextPurposePolicyService().max_budget(request.purpose,request.max_budget_chars) if ContextPurposePolicyService().known(request.purpose) else request.max_budget_chars or 0
        used=sum(i.budget_chars for i in items); safe=not any(x in {'secret_detected','raw_context_blocked'} for x in risks)
        return ContextBundle(request_id=request.request_id,purpose=request.purpose,scope=request.scope,items=items,citation_map=CitationMapBuilder().build(items),budget=ContextBudget(max_chars=maxc,used_chars=used,remaining_chars=max(0,maxc-used)),admission_decisions=decisions,rejected_items=rejs,warnings=warns,risk_flags=sorted(set(risks)),safe_for_prompt=safe)
class ContextBundleStore:
    def save(self,bundle): return ContextBundleRepository().save(bundle)
class ContextExplainService:
    def explain(self,bundle_id):
        b=ContextBundleRepository().get(bundle_id)
        if not b: raise FileNotFoundError(bundle_id)
        ex=[{'item_id':i.item_id,'source_ref':dump(i.source_ref),'reason':'admitted_by_context_kernel','citations':list(b.citation_map.keys())} for i in b.items]
        return ContextExplainResult(bundle_id=bundle_id,item_explanations=ex,rejection_explanations=b.rejected_items)
class ContextTraceService:
    def create(self,request,bundle,decisions):
        t=ContextTrace(request_id=request.request_id,bundle_id=bundle.bundle_id if bundle else None,steps=[{'step':'admission','decisions':[dump(d) for d in decisions]}]); ContextTraceRepository().save(t)
        if bundle: bundle.trace_id=t.trace_id; ContextBundleRepository().save(bundle)
        return t
    def get(self,trace_id): return ContextTraceRepository().get(trace_id)
class ContextAuditService:
    def record(self,action,details):
        path=PATHS.project_root/'data'/'runtime'/'context'/'audit'/'context_audit.jsonl'; path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a',encoding='utf-8') as f: f.write(json.dumps({'action':action,'details':redact_payload(details)},ensure_ascii=True)+'\n')
class SmartChunker:
    def chunk(self,text,source_ref=None,max_chars=1200): return [SmartChunk(text=text[i:i+max_chars],source_ref=source_ref,content_hash=h(text[i:i+max_chars])) for i in range(0,len(text),max_chars)] or [SmartChunk(text='',source_ref=source_ref,content_hash=h(''))]
class ChunkClassifier:
    def classify(self,chunk):
        low=chunk.text.lower(); kind='unknown'; trust='candidate'; conf=.3
        if 'schema_version' in low or 'policy' in low: kind='config_policy'; trust='verified'; conf=.9
        elif 'traceback' in low or 'error' in low: kind='error_trace'; trust='derived'; conf=.8
        elif 'task' in low: kind='task_summary'; trust='derived'; conf=.8
        elif 'artifact' in low: kind='artifact_summary'; trust='cited'; conf=.8
        elif low: kind='doc_section'; trust='cited'; conf=.7
        return ChunkClassification(chunk_id=chunk.chunk_id,chunk_type=kind,trust_level=trust,confidence=conf)
class ContextCompressionService:
    def compress(self,text,max_chars): return ContextCompressionResult(status='ok' if len(text)<=max_chars else 'truncated',original_chars=len(text),compressed_chars=min(len(text),max_chars))
class ContextConflictDetector:
    def detect(self,candidates):
        if any(c.source_type=='curated_memory' and c.freshness.status=='stale' for c in candidates) and any(c.source_type=='event_summary' for c in candidates): return [ContextWarning(code='stale_memory_vs_current_event',message='Memoria stale conflita com evento atual.')]
        return []
class ContextRawPolicyService:
    def raw_allowed(self,purpose,source_type): return source_type=='sanitized_raw_ref' and purpose=='debugger_analysis'


class ContextKernelService:
    def status(self):
        return ContextStatus(status='ok',enabled=True,context_admission_owner='context_kernel',context_bundle_builder_enabled=True,context_cache_enabled=True,smart_chunks_enabled=True,safe_for_prompt_required=True,raw_context_blocked=True,citations_required_for_contextual_claims=True).model_dump() | {'purposes':ContextPurposePolicyService().status().get('purposes',[])}
    def _prepare(self,request):
        candidates=ContextCandidateCollector().collect(request)
        if not ContextPurposePolicyService().known(request.purpose):
            decisions=ContextAdmissionServiceV2().admit(request,candidates); return candidates,decisions,ContextBundleBuilder().build(request,candidates,decisions)
        cached=ContextCacheService().get_bundle(request,candidates)
        if cached: return candidates,cached.admission_decisions,cached
        decisions=ContextAdmissionServiceV2().admit(request,candidates); bundle=ContextBundleBuilder().build(request,candidates,decisions); bundle.warnings.extend(ContextConflictDetector().detect(candidates)); return candidates,decisions,bundle
    def preview(self,request):
        candidates,decisions,bundle=self._prepare(request); ContextAuditService().record('preview',{'request_id':request.request_id,'purpose':request.purpose})
        return {'status':'ok' if ContextPurposePolicyService().known(request.purpose) else 'blocked','bundle':dump(bundle),'cache_used':bundle.metadata.cache_used}
    def build_ephemeral(self,request):
        candidates,decisions,bundle=self._prepare(request)
        trace=ContextTrace(request_id=request.request_id,bundle_id=bundle.bundle_id,steps=[{'step':'ephemeral_admission','decisions':[dump(d) for d in decisions]}])
        bundle.trace_id=trace.trace_id
        return ContextBuildResult(status='ok' if ContextPurposePolicyService().known(request.purpose) else 'blocked',bundle=bundle)
    def build(self,request):
        candidates,decisions,bundle=self._prepare(request); ContextBundleStore().save(bundle); trace=ContextTraceService().create(request,bundle,decisions); bundle.trace_id=trace.trace_id; ContextBundleStore().save(bundle)
        if ContextPurposePolicyService().known(request.purpose): ContextCacheService().remember(request,candidates,bundle)
        ContextAuditService().record('build',{'request_id':request.request_id,'bundle_id':bundle.bundle_id})
        return ContextBuildResult(status='ok' if ContextPurposePolicyService().known(request.purpose) else 'blocked',bundle=bundle)
    def admit(self,request):
        candidates=ContextCandidateCollector().collect(request); decisions=ContextAdmissionServiceV2().admit(request,candidates)
        return {'status':'ok' if ContextPurposePolicyService().known(request.purpose) else 'blocked','decisions':[dump(d) for d in decisions]}
    def injection_plan(self,bundle_id,role_id=None):
        bundle=ContextBundleRepository().get(bundle_id)
        if not bundle: raise FileNotFoundError(bundle_id)
        slots=[ContextPromptSlot(slot_id=layer,items=[i.item_id for i in bundle.items if i.layer==layer],max_chars=sum(i.budget_chars for i in bundle.items if i.layer==layer)) for layer in sorted({i.layer for i in bundle.items})]
        return ContextInjectionPlan(bundle_id=bundle_id,role_id=role_id,purpose=bundle.purpose,safe_for_prompt_assembly=bundle.safe_for_prompt,slots=slots,citation_map=bundle.citation_map,blocked_items=[r.candidate_id for r in bundle.rejected_items],warnings=bundle.warnings)

class ChatContextAdapter:
    def candidates(self,session_id,items):
        return [ContextCandidate(layer='chat_session',source_type='chat_message',source_ref=ContextSourceRef(source_type='chat_message',source_id=str(i.get('message_id',idx))),summary=str(i.get('content',''))[:120],content=str(i.get('content','')),priority=5,trust_level='derived') for idx,i in enumerate(items)]
class TaskContextAdapter:
    def candidates(self,cards):
        return [ContextCandidate(layer='active_task',source_type='task_card',source_ref=ContextSourceRef(source_type='task_card',source_id=str(c.get('task_id'))),summary=str(c.get('human_summary','task')),content=json.dumps(c,ensure_ascii=True),priority=7,trust_level='derived') for c in cards]
class PipelineContextAdapter(TaskContextAdapter): pass
class MemoryContextAdapter:
    def candidate(self,memory_id,summary,status='approved',freshness='fresh'):
        return ContextCandidate(layer='curated_memory',source_type='curated_memory',source_ref=ContextSourceRef(source_type='curated_memory',source_id=memory_id),summary=summary,content=summary,priority=6,trust_level='verified' if status=='approved' else 'candidate',freshness=ChunkFreshness(status=freshness),citations=[ContextCitation(source_ref=ContextSourceRef(source_type='curated_memory',source_id=memory_id),label='memory')])
class RAGContextAdapter:
    def candidate(self,hit_id,content,cited=True):
        ref=ContextSourceRef(source_type='rag_chunk',source_id=hit_id); citations=[ContextCitation(source_ref=ref,label='rag')] if cited else []
        return ContextCandidate(layer='governed_rag',source_type='rag_chunk',source_ref=ref,summary=content[:120],content=content,priority=6,trust_level='cited' if cited else 'candidate',citations=citations)
class ArtifactContextAdapter:
    def candidate(self,artifact_id,summary,path=None):
        return ContextCandidate(layer='attachments_artifacts',source_type='artifact_record',source_ref=ContextSourceRef(source_type='artifact_record',source_id=artifact_id,path=path),summary=summary,content=summary,priority=5,trust_level='cited',citations=[ContextCitation(source_ref=ContextSourceRef(source_type='artifact_record',source_id=artifact_id),label='artifact')])
class DebuggerContextAdapter:
    def candidate(self,trace_id,summary): return ContextCandidate(layer='debugger_eval_traces',source_type='debugger_trace',source_ref=ContextSourceRef(source_type='debugger_trace',source_id=trace_id),summary=summary,content=summary,priority=5,trust_level='derived')
class VisionOCRContextAdapter:
    def visual(self,run_id,summary,confidence=.8):
        ref=ContextSourceRef(source_type='visual_evidence',source_id=run_id); return ContextCandidate(layer='vision_ocr_context',source_type='visual_evidence',source_ref=ref,summary=summary,content=summary,priority=5,trust_level='cited',metadata={'confidence':confidence},citations=[ContextCitation(source_ref=ref,label='visual',confidence=confidence)])
    def ocr(self,run_id,text,confidence=.8):
        ref=ContextSourceRef(source_type='ocr_text_block',source_id=run_id); return ContextCandidate(layer='vision_ocr_context',source_type='ocr_text_block',source_ref=ref,summary=text[:120],content=text,priority=5,trust_level='cited',metadata={'confidence':confidence},citations=[ContextCitation(source_ref=ref,label='ocr',confidence=confidence)] if confidence>=.5 else [])
class EventContextAdapter:
    def candidate(self,event_type,summary): return ContextCandidate(layer='active_task',source_type='event_summary',source_ref=ContextSourceRef(source_type='event_summary',source_id=event_type),summary=summary,content=summary,priority=5,trust_level='derived')
