from aipinho.services.replay.replay_store_service import ReplayStoreService

def test_store_service_exposes_repositories():
    store = ReplayStoreService()
    assert store.snapshots is not None
    assert store.cases is not None
    assert store.runs is not None
