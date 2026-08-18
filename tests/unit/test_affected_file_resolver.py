from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.services.patching.affected_file_resolver import AffectedFileResolver


def test_affected_file_resolver_merges_paths():
    paths = AffectedFileResolver().resolve(["a.py"], [PatchEvidence(evidence_id="e", source_path="b.py", excerpt="x")])
    assert paths == ["a.py", "b.py"]
