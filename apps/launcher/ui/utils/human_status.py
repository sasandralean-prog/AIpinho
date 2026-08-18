from __future__ import annotations


def human_status(status: str | None) -> str:
    status = (status or "unknown").lower()
    if status in {"ok", "healthy", "running"}:
        return "Operacional"
    if status in {"degraded", "partial"}:
        return "Degradado"
    if status in {"blocked", "denied"}:
        return "Bloqueado"
    if status in {"down", "failed", "error"}:
        return "Indisponivel"
    return "Estado desconhecido"
