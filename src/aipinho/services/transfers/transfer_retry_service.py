class TransferRetryService:
    def next_state(self,current_status:str)->str:
        return "retry_queued" if current_status in {"failed","timeout","degraded"} else current_status
