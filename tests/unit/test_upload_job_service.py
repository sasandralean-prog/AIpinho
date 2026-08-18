import pytest
from aipinho.services.transfers.upload_job_service import UploadJobService
def test_upload_blocks_executable():
    with pytest.raises(ValueError): UploadJobService().create("bad.exe")
