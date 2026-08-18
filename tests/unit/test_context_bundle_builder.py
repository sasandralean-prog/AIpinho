from aipinho.services.context.context_core import ContextAdmissionServiceV2, ContextBundleBuilder
from tests.unit.context_test_helpers import request, candidate

def test_bundle_metadata_citation_rejected_safe():
    good=candidate(); bad=candidate(source_id='bad',cited=False)
    req=request(candidates=[good,bad]); decisions=ContextAdmissionServiceV2().admit(req,[good,bad]); bundle=ContextBundleBuilder().build(req,[good,bad],decisions)
    assert bundle.citation_map; assert bundle.rejected_items; assert bundle.safe_for_prompt
