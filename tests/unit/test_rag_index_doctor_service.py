from aipinho.services.rag.vector.rag_index_doctor_service import RAGIndexDoctorService


def test_rag_index_doctor_reports_namespace_health_without_legacy_store():
    result = RAGIndexDoctorService().doctor("coder_rag")

    assert result["status"] in {"healthy", "missing", "blocked"}
    assert result["namespace_id"] == "coder_rag"
    if result["status"] != "missing":
        assert result["index"]["manifest_path"]
