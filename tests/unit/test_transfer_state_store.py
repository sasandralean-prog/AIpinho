from apps.launcher.ui.state.transfer_state_store import TransferStateStore
def test_transfer_store_snapshots():
    s=TransferStateStore(); s.set("job","queued"); assert s.snapshot()["job"]=="queued"
