from __future__ import annotations


def degraded_message(endpoint: str, error: str | None) -> str:
    return f"{endpoint} indisponivel: {error or 'sem resposta'}"
