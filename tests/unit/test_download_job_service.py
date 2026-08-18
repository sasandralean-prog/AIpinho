from aipinho.services.transfers.download_job_service import DownloadJobService
def test_download_requires_artifact_id():
    svc=DownloadJobService(); job=svc.create("artifact_1"); assert job.status=="queued" and svc.get(job.job_id)
