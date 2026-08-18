from pathlib import Path
import sys


def test_legacy_governance_quarantine_files_are_not_imported() -> None:
    quarantine = Path(r"C:\Dev\AIpinho\quarantine\legacy\governance")
    imported = [
        str(getattr(module, "__file__", ""))
        for module in sys.modules.values()
        if getattr(module, "__file__", None) and str(getattr(module, "__file__")).startswith(str(quarantine))
    ]
    assert imported == [], "LEGACY_GOVERNANCE_IMPORT_FORBIDDEN"
