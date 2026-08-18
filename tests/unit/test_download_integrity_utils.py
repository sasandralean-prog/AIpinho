from apps.launcher.ui.utils.download_integrity import verify_sha256
def test_download_integrity_verifies_hash():
    assert verify_sha256(b"abc","ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
