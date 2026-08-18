from aipinho.services.context.context_core import ChatContextAdapter, TaskContextAdapter, MemoryContextAdapter, RAGContextAdapter, ArtifactContextAdapter, DebuggerContextAdapter, VisionOCRContextAdapter, EventContextAdapter

def test_context_adapters_create_candidates():
    assert ChatContextAdapter().candidates('s',[{'message_id':'m','content':'ola'}])
    assert TaskContextAdapter().candidates([{'task_id':'t','human_summary':'task'}])
    assert MemoryContextAdapter().candidate('m','memoria').source_type=='curated_memory'
    assert RAGContextAdapter().candidate('r','rag').citations
    assert ArtifactContextAdapter().candidate('a','art').source_ref.source_id=='a'
    assert DebuggerContextAdapter().candidate('tr','debug').layer=='debugger_eval_traces'
    assert VisionOCRContextAdapter().visual('v','img').citations
    assert EventContextAdapter().candidate('message_received','evento').source_type=='event_summary'
