from aipinho.services.transfers.transfer_retry_service import TransferRetryService
def test_retry_only_failed_like_states():
    assert TransferRetryService().next_state("failed")=="retry_queued"; assert TransferRetryService().next_state("completed")=="completed"
