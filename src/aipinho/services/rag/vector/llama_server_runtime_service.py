from __future__ import annotations

import atexit
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aipinho.core.paths import PATHS
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass
class LlamaServerResponse:
    status: str
    data: Any = None
    warnings: list[str] | None = None
    blocked_reasons: list[str] | None = None
    endpoint: str | None = None
    latency_ms: int = 0


class LlamaServerRuntimeService:
    _processes: dict[str, subprocess.Popen] = {}

    def __init__(
        self,
        config_path: Path | None = None,
        config: dict[str, Any] | None = None,
        model_registry: ModelRegistryService | None = None,
        provider_registry: ProviderRegistryService | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "rag" / "llama_server_runtime.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()

    def embed(self, texts: list[str], *, model_id: str) -> LlamaServerResponse:
        section = self._section("embedding")
        if not section.get("enabled", False):
            return LlamaServerResponse(status="blocked", blocked_reasons=["llama_server_embedding_disabled"])
        texts = [self._limit_input(text) for text in texts]
        ready = self._ensure_ready("embedding", model_id=model_id)
        if ready.status != "ok":
            return ready
        payload = {"model": model_id, "input": texts}
        response = self._post_first("embedding", payload)
        if response.status != "ok":
            return response
        vectors = self._extract_embeddings(response.data)
        if len(vectors) != len(texts):
            return LlamaServerResponse(
                status="error",
                warnings=["embedding_response_shape_mismatch"],
                endpoint=response.endpoint,
                latency_ms=response.latency_ms,
            )
        response.data = vectors
        return response

    def rerank(self, *, query: str, documents: list[str], model_id: str, top_k: int) -> LlamaServerResponse:
        section = self._section("reranker")
        if not section.get("enabled", False):
            return LlamaServerResponse(status="blocked", blocked_reasons=["llama_server_reranker_disabled"])
        query = self._limit_input(query)
        documents = [self._limit_input(document) for document in documents]
        ready = self._ensure_ready("reranker", model_id=model_id)
        if ready.status != "ok":
            return ready
        payloads = [
            {"model": model_id, "query": query, "documents": documents, "top_n": top_k},
            {"model": model_id, "query": query, "input": documents, "top_n": top_k},
        ]
        last_response = LlamaServerResponse(status="error", warnings=["reranker_endpoint_unavailable"])
        for payload in payloads:
            response = self._post_first("reranker", payload)
            if response.status == "ok":
                scores = self._extract_rerank_scores(response.data, count=len(documents))
                if scores:
                    response.data = scores
                    return response
                last_response = LlamaServerResponse(
                    status="error",
                    warnings=["reranker_response_shape_mismatch"],
                    endpoint=response.endpoint,
                    latency_ms=response.latency_ms,
                )
            else:
                last_response = response
        return last_response

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "llama_server_runtime",
            "embedding": self._service_status("embedding"),
            "reranker": self._service_status("reranker"),
        }

    def _ensure_ready(self, service_id: str, *, model_id: str) -> LlamaServerResponse:
        section = self._section(service_id)
        if self._test_runtime_blocked():
            return LlamaServerResponse(status="error", warnings=[f"{service_id}_real_runtime_disabled_in_test_profile"])
        status = self._service_status(service_id)
        if status["reachable"]:
            return LlamaServerResponse(status="ok")
        if not section.get("auto_start", False):
            return LlamaServerResponse(status="error", warnings=[f"{service_id}_server_unreachable", "auto_start_disabled"])
        started = self._start(service_id, model_id=model_id)
        if started.status != "ok":
            return started
        return LlamaServerResponse(status="ok")

    def _start(self, service_id: str, *, model_id: str) -> LlamaServerResponse:
        section = self._section(service_id)
        key = self._key(service_id)
        existing = self._processes.get(key)
        if existing is not None and existing.poll() is None:
            return LlamaServerResponse(status="ok")

        model = self.model_registry.get_runtime_model(model_id)
        if model is None or not model.model_path:
            return LlamaServerResponse(status="blocked", blocked_reasons=[f"{service_id}_model_path_missing"])
        provider = self.provider_registry.get_provider(str(section.get("provider_id") or model.provider_id))
        executable = section.get("server_executable_path") or (provider.server_executable_path if provider else None) or (provider.executable_path if provider else None)
        if not executable:
            return LlamaServerResponse(status="blocked", blocked_reasons=[f"{service_id}_server_executable_missing"])

        argv = [
            str(executable),
            "--model",
            str(model.model_path),
            "--host",
            str(self._host()),
            "--port",
            str(self._port(service_id)),
            "--alias",
            model_id,
            *[str(arg) for arg in section.get("server_args", []) or []],
        ]
        creationflags = 0
        if self._defaults().get("isolate_process_group", True):
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if self._defaults().get("no_window", True):
            creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                creationflags=creationflags,
            )
        except OSError as exc:
            return LlamaServerResponse(status="error", warnings=[f"{service_id}_server_start_failed", type(exc).__name__])
        self._processes[key] = proc
        deadline = time.time() + int(self._defaults().get("startup_timeout_seconds", 45) or 45)
        while time.time() < deadline:
            if proc.poll() is not None:
                return LlamaServerResponse(status="error", warnings=[f"{service_id}_server_exited"], blocked_reasons=[f"exit_code:{proc.returncode}"])
            if self._service_status(service_id)["reachable"]:
                return LlamaServerResponse(status="ok")
            time.sleep(0.5)
        return LlamaServerResponse(status="error", warnings=[f"{service_id}_server_startup_timeout"])

    def _post_first(self, service_id: str, payload: dict[str, Any]) -> LlamaServerResponse:
        last_warning = f"{service_id}_endpoint_unavailable"
        for path in self._section(service_id).get("endpoint_paths", []) or []:
            started = time.time()
            try:
                data = json.dumps(payload).encode("utf-8")
                request = Request(
                    self._url(path, service_id=service_id),
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=float(self._defaults().get("request_timeout_seconds", 30) or 30)) as response:
                    body = response.read().decode("utf-8", errors="replace")
                return LlamaServerResponse(
                    status="ok",
                    data=json.loads(body or "{}"),
                    endpoint=path,
                    latency_ms=int((time.time() - started) * 1000),
                )
            except HTTPError as exc:
                last_warning = f"http_{exc.code}:{path}"
            except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last_warning = f"{type(exc).__name__}:{path}"
        return LlamaServerResponse(status="error", warnings=[last_warning])

    def _service_status(self, service_id: str) -> dict[str, object]:
        process = self._processes.get(self._key(service_id))
        process_alive = process is not None and process.poll() is None
        reachable = False
        for path in self._defaults().get("health_paths", []) or []:
            try:
                with urlopen(self._url(str(path), service_id=service_id), timeout=1.5) as response:
                    reachable = 200 <= int(response.status) < 500
                if reachable:
                    break
            except Exception:
                continue
        return {
            "enabled": bool(self._section(service_id).get("enabled", False)),
            "auto_start": bool(self._section(service_id).get("auto_start", False)),
            "host": self._host(),
            "port": self._port(service_id),
            "reachable": reachable,
            "process_alive": process_alive,
        }

    def _extract_embeddings(self, payload: Any) -> list[list[float]]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, list):
            vectors = []
            for item in data:
                if isinstance(item, dict) and isinstance(item.get("embedding"), list):
                    vectors.append([float(value) for value in item["embedding"]])
            return vectors
        embedding = payload.get("embedding")
        if isinstance(embedding, list) and embedding and isinstance(embedding[0], list):
            return [[float(value) for value in vector] for vector in embedding]
        if isinstance(embedding, list):
            return [[float(value) for value in embedding]]
        return []

    def _extract_rerank_scores(self, payload: Any, *, count: int) -> list[tuple[int, float]]:
        if not isinstance(payload, dict):
            return []
        raw = payload.get("results") or payload.get("data") or payload.get("rankings")
        if not isinstance(raw, list):
            return []
        scores: list[tuple[int, float]] = []
        for position, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            index = int(item.get("index", item.get("document_index", position)))
            score = float(item.get("relevance_score", item.get("score", item.get("rank_score", 0.0))))
            if 0 <= index < count:
                scores.append((index, score))
        return scores

    def _section(self, service_id: str) -> dict[str, Any]:
        value = self.config.get(service_id, {})
        return value if isinstance(value, dict) else {}

    def _defaults(self) -> dict[str, Any]:
        value = self.config.get("server_defaults", {})
        return value if isinstance(value, dict) else {}

    def _test_runtime(self) -> dict[str, Any]:
        value = self.config.get("test_runtime", {})
        return value if isinstance(value, dict) else {}

    def _host(self) -> str:
        return str(self._defaults().get("host", "127.0.0.1"))

    def _limit_input(self, value: str) -> str:
        max_chars = int(self._defaults().get("max_input_chars", 12000) or 12000)
        return value[:max_chars] if max_chars > 0 else value

    def _test_runtime_blocked(self) -> bool:
        test_runtime = self._test_runtime()
        if not bool(test_runtime.get("disable_real_runtime_under_pytest", True)):
            return False
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        opt_in_env = str(test_runtime.get("opt_in_env") or "AIPINHO_ENABLE_REAL_RAG_RUNTIME_TESTS")
        return os.environ.get(opt_in_env, "").lower() not in {"1", "true", "yes", "on"}

    def _port(self, service_id: str) -> int:
        return int(self._section(service_id).get("port") or 8080)

    def _url(self, path: str, *, service_id: str | None = None) -> str:
        selected = service_id or "embedding"
        return f"http://{self._host()}:{self._port(selected)}{path}"

    def _key(self, service_id: str) -> str:
        return f"{service_id}:{self._host()}:{self._port(service_id)}"


def _cleanup() -> None:
    for process in list(LlamaServerRuntimeService._processes.values()):
        if process.poll() is None:
            process.terminate()


atexit.register(_cleanup)
