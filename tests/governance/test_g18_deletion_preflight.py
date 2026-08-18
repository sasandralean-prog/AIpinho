import json
from pathlib import Path


def test_g18_deletion_manifest_only_marks_quarantine_files_delete_ready_if_inside_quarantine() -> None:
    manifest_path = Path(r"C:\Dev\AIpinho\reports\governance_block_c\G18_legacy_deletion_manifest.json")
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    quarantine_root = Path(r"C:\Dev\AIpinho\quarantine\legacy\governance").resolve()
    for item in manifest.get("items", []):
        if item.get("delete_decision") != "delete_ready":
            continue
        path = Path(item["quarantine_path"]).resolve()
        assert str(path).startswith(str(quarantine_root))
