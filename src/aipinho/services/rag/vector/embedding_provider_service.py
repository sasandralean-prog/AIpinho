from __future__ import annotations

import hashlib
import math
import re

from aipinho.schemas.rag.vector.contracts import EmbeddingRequest, EmbeddingResult, RAGChunk
from aipinho.services.rag.vector.embedding_runtime_gate import EmbeddingRuntimeGate
from aipinho.services.rag.vector.llama_server_runtime_service import LlamaServerRuntimeService
from aipinho.services.rag.vector.rag_chunk_validator import RAGChunkValidator
from aipinho.services.rag.vector.config import rag_config


TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]{2,}")


class EmbeddingProviderService:
    def __init__(
        self,
        gate: EmbeddingRuntimeGate | None = None,
        validator: RAGChunkValidator | None = None,
        runtime: LlamaServerRuntimeService | None = None,
    ) -> None:
        self.gate = gate or EmbeddingRuntimeGate()
        self.validator = validator or RAGChunkValidator()
        self.runtime = runtime or LlamaServerRuntimeService()
        self.config = rag_config("embedding_policy.yaml")

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        gate = self.gate.decide(request.model_id)
        if not gate["allowed"]:
            return EmbeddingResult(status="blocked", model_id=request.model_id, warnings=list(gate.get("warnings", [])), blocked_reasons=list(gate.get("blocked_reasons", [])))
        validation = self.validator.validate_many(request.chunks)
        if not validation["valid"]:
            return EmbeddingResult(status="blocked", model_id=request.model_id, warnings=list(gate.get("warnings", [])), blocked_reasons=list(validation.get("blocked_reasons", [])))
        texts = [chunk.text + " " + chunk.source.citation.excerpt for chunk in request.chunks]
        runtime_result = self.runtime.embed(texts, model_id=request.model_id)
        warnings = list(dict.fromkeys([*list(gate.get("warnings", [])), *(runtime_result.warnings or [])]))
        if runtime_result.status == "ok" and isinstance(runtime_result.data, list):
            embeddings = {
                chunk.chunk_id: [float(value) for value in runtime_result.data[index]]
                for index, chunk in enumerate(request.chunks)
            }
            return EmbeddingResult(
                status="ok",
                model_id=request.model_id,
                embeddings=embeddings,
                real_runtime_attempted=True,
                deterministic_fallback_used=False,
                warnings=warnings,
            )
        if not self._fallback_allowed():
            return EmbeddingResult(
                status="error",
                model_id=request.model_id,
                real_runtime_attempted=True,
                deterministic_fallback_used=False,
                warnings=warnings,
                blocked_reasons=list(runtime_result.blocked_reasons or []),
            )
        embeddings = {chunk.chunk_id: self._embedding(chunk) for chunk in request.chunks}
        return EmbeddingResult(
            status="ok",
            model_id=request.model_id,
            embeddings=embeddings,
            real_runtime_attempted=True,
            deterministic_fallback_used=True,
            warnings=list(dict.fromkeys([*warnings, "embedding_runtime_fallback_used"])),
        )

    def _embedding(self, chunk: RAGChunk) -> list[float]:
        return self._lexical_embedding(chunk.text + " " + chunk.source.citation.excerpt)

    def embed_text(self, text: str, *, model_id: str = "qwen3_embedding_4b_q5_k_m") -> list[float]:
        gate = self.gate.decide(model_id)
        if gate["allowed"]:
            runtime_result = self.runtime.embed([text], model_id=model_id)
            if runtime_result.status == "ok" and isinstance(runtime_result.data, list) and runtime_result.data:
                return [float(value) for value in runtime_result.data[0]]
        return self._lexical_embedding(text)

    def _lexical_embedding(self, text: str) -> list[float]:
        dimensions = int((self.config.get("embedding", {}) or {}).get("dimensions", 16))
        vector = [0.0 for _ in range(dimensions)]
        tokens = [token.lower() for token in TOKEN_RE.findall(text)]
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
            if len(token) > 4:
                prefix = token[:4]
                prefix_digest = hashlib.sha256(prefix.encode("utf-8")).digest()
                prefix_index = int.from_bytes(prefix_digest[:4], "big") % dimensions
                vector[prefix_index] += 0.25
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [round(value / norm, 6) for value in vector]

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "embedding_provider",
            "model_id": "qwen3_embedding_4b_q5_k_m",
            "chat_use_enabled": False,
            "runtime": self.runtime.status().get("embedding", {}),
            "deterministic_fallback": "lexical_hashing" if self._fallback_allowed() else "disabled",
        }

    def _fallback_allowed(self) -> bool:
        policy = self.config.get("embedding", {}) if isinstance(self.config.get("embedding", {}), dict) else {}
        return bool(policy.get("allow_deterministic_fallback_when_runtime_unavailable", True))
