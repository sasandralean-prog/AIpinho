from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.codex_governed_execution import CodexGovernedContract
from aipinho.schemas.events.contracts import utc_now_iso


class CodexGovernedContractStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "codex_agent" / "contracts"

    def save(self, contract: CodexGovernedContract) -> CodexGovernedContract:
        self.root.mkdir(parents=True, exist_ok=True)
        contract = contract.model_copy(update={"updated_at": utc_now_iso()})
        self._path(contract.contract_id).write_text(
            json.dumps(contract.model_dump(), ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        return contract

    def get(self, contract_id: str) -> CodexGovernedContract | None:
        path = self._path(contract_id)
        if not path.exists():
            return None
        return CodexGovernedContract.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )

    def list(self, *, session_id: str | None = None) -> list[CodexGovernedContract]:
        if not self.root.exists():
            return []
        contracts = [
            CodexGovernedContract.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
            for path in self.root.glob("codex_contract_*.json")
        ]
        if session_id:
            contracts = [
                contract for contract in contracts if contract.session_id == session_id
            ]
        return sorted(contracts, key=lambda contract: contract.created_at, reverse=True)

    def _path(self, contract_id: str) -> Path:
        if not contract_id.startswith("codex_contract_") or any(
            token in contract_id for token in ("/", "\\", "..")
        ):
            raise ValueError("invalid_codex_contract_id")
        return self.root / f"{contract_id}.json"
