from __future__ import annotations

import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest, ToolInvocationResult
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService


class AgentLocalActionPlanner:
    """Plans small explicit local actions without bypassing Tool Gateway policy."""

    def __init__(self, tool_gateway: AgentToolGatewayService | None = None) -> None:
        self.tool_gateway = tool_gateway or AgentToolGatewayService()

    def run_explicit_create_file(
        self,
        *,
        agent_id: str,
        run_id: str,
        prompt: str,
        workspace_context: str | None,
        requested_capabilities: list[str],
        content_hint: str = "",
        approval_id: str | None = None,
        execution_mode: str = "governed_autorun",
        metadata_sanitized: dict[str, Any] | None = None,
    ) -> ToolInvocationResult | None:
        if "create_file" not in set(requested_capabilities or []):
            return None
        if not workspace_context:
            return None
        filename = self.extract_requested_filename(prompt)
        if not filename:
            return None
        target_path = str(Path(workspace_context) / filename)
        content = self.content_for_requested_file(prompt, content_hint, workspace_context=workspace_context)
        return self.tool_gateway.invoke(
            agent_id,
            run_id,
            "create_file",
            ToolInvocationCreateRequest(
                operation_type="create_file",
                workspace_id=self.infer_workspace_id(workspace_context),
                path_ref=target_path,
                approval_id=approval_id,
                input={
                    "content": content,
                    "overwrite": True,
                },
                metadata_sanitized={
                    **(metadata_sanitized or {}),
                    "execution_mode": execution_mode,
                    "planner_mode": "explicit_create_file_request",
                },
            ),
        )

    def run_explicit_modify_file(
        self,
        *,
        agent_id: str,
        run_id: str,
        prompt: str,
        workspace_context: str | None,
        requested_capabilities: list[str],
        content_hint: str = "",
        approval_id: str | None = None,
        execution_mode: str = "governed_autorun",
        metadata_sanitized: dict[str, Any] | None = None,
    ) -> ToolInvocationResult | None:
        if "modify_file" not in set(requested_capabilities or []):
            return None
        if not workspace_context:
            return None
        filename = self.extract_requested_filename(prompt)
        if not filename:
            return None
        target_path = Path(workspace_context) / filename
        if not target_path.exists() or not target_path.is_file():
            return None
        original_bytes = target_path.read_bytes()
        original = original_bytes.decode("utf-8", errors="replace")
        content = self.content_for_modified_file(prompt, original, content_hint)
        expected_contains = self.extract_requested_section(prompt) or self.extract_requested_content(prompt)
        expected_hash = hashlib.sha256(original_bytes).hexdigest()
        return self.tool_gateway.invoke(
            agent_id,
            run_id,
            "modify_file",
            ToolInvocationCreateRequest(
                operation_type="modify_file",
                workspace_id=self.infer_workspace_id(workspace_context),
                path_ref=str(target_path),
                approval_id=approval_id,
                input={
                    "content": content,
                    "expected_hash": expected_hash,
                    "expected_contains": expected_contains,
                },
                metadata_sanitized={
                    **(metadata_sanitized or {}),
                    "execution_mode": execution_mode,
                    "planner_mode": "explicit_modify_file_request",
                },
            ),
        )

    def run_inferred_ui_text_update(
        self,
        *,
        agent_id: str,
        run_id: str,
        prompt: str,
        workspace_context: str | None,
        requested_capabilities: list[str],
        content_hint: str = "",
        approval_id: str | None = None,
        execution_mode: str = "governed_autorun",
        metadata_sanitized: dict[str, Any] | None = None,
    ) -> ToolInvocationResult | None:
        if "modify_file" not in set(requested_capabilities or []):
            return None
        if not workspace_context:
            return None
        visible_text = self.extract_requested_visible_text(prompt)
        if not visible_text:
            return None
        target_path = self.infer_ui_source_file(workspace_context)
        if target_path is None:
            return None
        original_bytes = target_path.read_bytes()
        original = original_bytes.decode("utf-8", errors="replace")
        content = self.content_for_ui_text_update(original, visible_text, prompt=prompt)
        expected_contains = self.expected_visible_ui_marker(content, visible_text) or visible_text
        expected_hash = hashlib.sha256(original_bytes).hexdigest()
        return self.tool_gateway.invoke(
            agent_id,
            run_id,
            "modify_file",
            ToolInvocationCreateRequest(
                operation_type="modify_file",
                workspace_id=self.infer_workspace_id(workspace_context),
                path_ref=str(target_path),
                approval_id=approval_id,
                input={
                    "content": content,
                    "expected_hash": expected_hash,
                    "expected_contains": expected_contains,
                },
                metadata_sanitized={
                    **(metadata_sanitized or {}),
                    "execution_mode": execution_mode,
                    "planner_mode": "inferred_ui_text_update",
                    "target_resolution": "infer_ui_source",
                    "inferred_target_path": str(target_path),
                },
            ),
        )

    def extract_requested_filename(self, prompt: str) -> str | None:
        patterns = [
            r"(?:arquivo|ficheiro|file)\s+(?:chamado|nomeado|com\s+nome|named)\s+[`\"']?([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']?",
            r"(?:arquivo|ficheiro|file)\s+[`\"']?([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']?",
            r"(?:chamado|nomeado|named)\s+[`\"']?([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']?",
            r"(?:crie|criar|gerar|gere|salve|escreva)\s+(?:um\s+)?(?:arquivo|ficheiro|file)?\s*[`\"']?([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']?",
            r"(?:atualize|atualizar|modifique|modificar|altere|alterar|edite|editar)\s+(?:o\s+|a\s+)?(?:arquivo|ficheiro|file)?\s*[`\"']?([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']?",
            r"(?:em|para|at|to)\s*[:=]?\s*[`\"']?([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']?",
            r"[`\"']([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})[`\"']",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE | re.MULTILINE)
            if not match:
                continue
            line_start = prompt.rfind("\n", 0, match.start()) + 1
            line_prefix = prompt[line_start:match.start()]
            if re.search(r"^\s*(?:[-*]\s*)?\d+[.)]\s*$", line_prefix):
                continue
            candidate = re.sub(r"^(chamado|nomeado|named)\s+", "", match.group(1).strip(), flags=re.IGNORECASE)
            if re.match(r"^\s*\d+[.)]\s+", candidate):
                continue
            filename = self._safe_relative_filename(candidate)
            if filename:
                return filename
        return None

    def extract_requested_visible_text(self, prompt: str) -> str | None:
        patterns = [
            r"(?:texto|frase|mensagem)\s+vis[Ã­i]vel\s+[`\"']([^`\"'\n]+)[`\"']",
            r"(?:visible\s+(?:text|message))\s+[`\"']([^`\"'\n]+)[`\"']",
            r"(?:adicione|adicionar|inclua|incluir|coloque|colocar)\s+(?:o\s+)?(?:texto|frase|mensagem)\s+vis[Ã­i]vel\s+[`\"']([^`\"'\n]+)[`\"']",
            r"[`\"']([^`\"'\n]{6,240})[`\"']",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if not match:
                continue
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            if value and "." not in value[:4]:
                return value[:240]
        return None

    def infer_ui_source_file(self, workspace_context: str | None) -> Path | None:
        if not workspace_context:
            return None
        root = Path(workspace_context)
        try:
            resolved = root.resolve()
        except Exception:
            return None
        if not resolved.exists() or not resolved.is_dir():
            return None
        ignored_parts = {
            ".git",
            ".gradle",
            ".idea",
            ".kotlin",
            ".venv",
            "__pycache__",
            "build",
            "dist",
            "node_modules",
            "reports",
            "docs",
            "out",
            "target",
        }
        allowed_suffixes = {".kt", ".java", ".tsx", ".jsx", ".ts", ".js", ".html", ".py"}
        candidates: list[tuple[int, int, Path]] = []
        for path in resolved.rglob("*"):
            try:
                relative = path.relative_to(resolved)
            except ValueError:
                continue
            if set(part.casefold() for part in relative.parts) & ignored_parts:
                continue
            if not path.is_file() or path.suffix.casefold() not in allowed_suffixes:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            score = self._ui_source_score(relative.as_posix(), text)
            if score > 0:
                candidates.append((score, -len(relative.parts), path))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]

    def _ui_source_score(self, relative_path: str, text: str) -> int:
        path = relative_path.casefold()
        lowered = text.casefold()
        score = 0
        path_markers = ("ui", "screen", "dashboard", "home", "main", "app", "activity", "view")
        score += sum(3 for marker in path_markers if marker in path)
        content_markers = (
            "@composable",
            "text(",
            "materialtheme",
            "column(",
            "row(",
            "surface(",
            "fun ",
            "return (",
            "<body",
            "render(",
            "dashboard",
            "welcome",
        )
        score += sum(2 for marker in content_markers if marker in lowered)
        if "test" in path or "androidtest" in path:
            score -= 8
        return score

    def content_for_ui_text_update(self, original: str, visible_text: str, *, prompt: str = "") -> str:
        if self._visible_text_is_rendered(original, visible_text):
            return original
        escaped = self._escape_kotlin_string(visible_text)
        const_name = "GOVERNED_VISIBLE_TEXT" if f'GOVERNED_VISIBLE_TEXT = "{escaped}"' in original else None
        text_expression = const_name or f'"{escaped}"'
        inserted = self._insert_visible_text_in_ui_function(original, text_expression, prompt=prompt)
        if inserted != original:
            return inserted
        separator = "" if original.endswith("\n") else "\n"
        return f'{original}{separator}\nprivate const val GOVERNED_VISIBLE_TEXT = "{escaped}"\n'

    def expected_visible_ui_marker(self, content: str, visible_text: str) -> str | None:
        escaped = self._escape_kotlin_string(visible_text)
        literal_marker = f'Text("{escaped}"'
        const_marker = "Text(GOVERNED_VISIBLE_TEXT"
        if literal_marker in content:
            return literal_marker
        if const_marker in content and f'GOVERNED_VISIBLE_TEXT = "{escaped}"' in content:
            return const_marker
        return None

    def _visible_text_is_rendered(self, original: str, visible_text: str) -> bool:
        return self.expected_visible_ui_marker(original, visible_text) is not None

    def _insert_visible_text_in_ui_function(self, original: str, text_expression: str, *, prompt: str = "") -> str:
        lines = original.splitlines(keepends=True)
        if not lines:
            return original
        lowered_prompt = prompt.casefold()
        preferred_names = ["dashboard", "home", "welcome", "main", "screen"]
        if "dashboard" in lowered_prompt:
            preferred_names.insert(0, "dashboard")
        function_indexes: list[tuple[int, int]] = []
        for index, line in enumerate(lines):
            match = re.search(r"\bfun\s+([A-Za-z0-9_]+)\s*\(", line)
            if not match:
                continue
            name = match.group(1).casefold()
            score = 1
            for rank, marker in enumerate(preferred_names):
                if marker in name:
                    score += 20 - rank
            function_indexes.append((score, index))
        function_indexes.sort(reverse=True)
        for _, function_index in function_indexes:
            insert_index = self._first_layout_line_after(lines, function_index)
            if insert_index is not None:
                return self._insert_text_line(lines, insert_index, text_expression)
        insert_index = self._first_layout_line_after(lines, 0)
        if insert_index is not None:
            return self._insert_text_line(lines, insert_index, text_expression)
        return original

    def _first_layout_line_after(self, lines: list[str], start_index: int) -> int | None:
        for index in range(start_index, min(len(lines), start_index + 120)):
            stripped = lines[index].strip()
            if not stripped:
                continue
            if re.search(r"\b(Column|Row|Box|Surface|Card|NeonCard)\b", stripped) and "{" in stripped:
                return index
        return None

    def _insert_text_line(self, lines: list[str], layout_line_index: int, text_expression: str) -> str:
        line = lines[layout_line_index]
        indent_match = re.match(r"(\s*)", line)
        indent = (indent_match.group(1) if indent_match else "") + "    "
        newline = "\r\n" if line.endswith("\r\n") else "\n"
        output = list(lines)
        output.insert(layout_line_index + 1, f"{indent}Text({text_expression}){newline}")
        return "".join(output)

    def _escape_kotlin_string(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("\"", "\\\"")

    def _safe_relative_filename(self, candidate: str) -> str | None:
        value = candidate.strip().strip("`\"'")
        if not value:
            return None
        normalized = re.sub(r"[\\/]+", "/", value.replace("\\", "/")).strip("/")
        lowered = normalized.casefold()
        for marker in (" em ", " para ", " at ", " to "):
            if marker in lowered:
                suffix = normalized[lowered.rfind(marker) + len(marker):].strip(" /")
                if "/" in suffix and re.search(r"\.[A-Za-z0-9]{1,12}$", suffix):
                    normalized = suffix
                    lowered = normalized.casefold()
                    break
        if not normalized:
            return None
        if re.match(r"^[A-Za-z]:", normalized) or normalized.startswith("//"):
            return None
        path = Path(normalized)
        if path.is_absolute():
            return None
        parts = [part for part in normalized.split("/") if part and part != "."]
        if not parts or any(part == ".." for part in parts):
            return None
        if any(re.search(r"[\x00-\x1f]", part) for part in parts):
            return None
        filename = parts[-1]
        if filename.startswith(".") or "." not in filename:
            return None
        return "/".join(parts)

    def infer_workspace_id(self, workspace_context: str) -> str | None:
        try:
            resolved = str(Path(workspace_context).resolve())
            workspace = self.tool_gateway.resolver.resolve(path_ref=resolved, access="write")
            if workspace.allowed:
                return workspace.workspace_id
        except Exception:
            return None
        return None

    def content_for_requested_file(self, prompt: str, content_hint: str = "", *, workspace_context: str | None = None) -> str:
        explicit_content = self.extract_requested_content(prompt)
        if explicit_content is not None:
            return explicit_content.rstrip("\n") + "\n"
        clean_hint = content_hint.strip()
        if clean_hint and "```" in clean_hint:
            blocks = re.findall(r"```(?:[A-Za-z0-9_-]+)?\s*(.*?)```", clean_hint, flags=re.DOTALL)
            if blocks:
                return blocks[-1].strip() + "\n"
        if clean_hint and not self.looks_like_failed_content(clean_hint):
            return clean_hint + "\n"
        source_diagnosis = self.source_diagnosis_report(prompt, workspace_context)
        if source_diagnosis:
            return source_diagnosis
        workspace_summary = self.workspace_summary(workspace_context) if workspace_context else None
        if workspace_summary:
            return self.report_from_workspace_summary(prompt, workspace_summary)
        return (
            "Relatorio solicitado\n\n"
            "Objetivo\n"
            "Registrar uma resposta textual governada para a solicitacao do usuario.\n\n"
            "Solicitacao resumida\n"
            f"{prompt.strip()}\n\n"
            "Observacao\n"
            "Este arquivo foi criado pelo fluxo de ferramentas governadas, com workspace e policy avaliados antes da escrita.\n"
        )

    def source_diagnosis_report(self, prompt: str, workspace_context: str | None) -> str | None:
        if not workspace_context:
            return None
        lowered = prompt.casefold()
        diagnosis_terms = ("diagnost", "investig", "verifique", "analise", "audite", "avali")
        strong_persistence_terms = (
            "persist",
            "dados salvos",
            "demo",
            "demodata",
            "storage",
            "repository",
            "repositorio",
        )
        persistence_terms = (
            "recarrega",
            "load",
            "save",
            "export",
            "import",
            "json",
            *strong_persistence_terms,
        )
        if not any(term in lowered for term in diagnosis_terms):
            return None
        if self._requested_report_items(prompt) and not any(term in lowered for term in strong_persistence_terms):
            return None
        if not any(term in lowered for term in persistence_terms):
            return None
        root = Path(workspace_context)
        try:
            resolved = root.resolve()
        except Exception:
            return None
        if not resolved.exists() or not resolved.is_dir():
            return None
        evidence = self._collect_source_diagnosis_evidence(
            resolved,
            [
                "persist",
                "repository",
                "storage",
                "datastore",
                "load",
                "save",
                "export",
                "demo",
                "demodata",
                "write",
            ],
        )
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        verdict = self._persistence_verdict(evidence)
        primary = evidence[0] if evidence else None
        load_functions = self._function_names_from_evidence(evidence, ("load",))
        save_functions = self._function_names_from_evidence(evidence, ("save", "write", "export"))
        evidence_text = self._render_source_evidence(evidence)
        return (
            "Relatorio solicitado\n\n"
            "Titulo\n"
            "Diagnostico dirigido de persistencia\n\n"
            "Data\n"
            f"{generated_at}\n\n"
            "Workspace\n"
            f"{resolved}\n\n"
            "Resumo\n"
            "Foi realizada leitura dirigida do codigo-fonte para verificar se o app carrega dados persistidos ou depende apenas de dados demonstrativos.\n\n"
            "Arquivo responsavel pela persistencia\n"
            f"{primary['relative_path'] if primary else 'Nenhum arquivo responsavel identificado pela leitura dirigida.'}\n\n"
            "Funcao de load\n"
            f"{', '.join(load_functions) if load_functions else 'Nao identificada com confianca nos arquivos amostrados.'}\n\n"
            "Funcao de save/export\n"
            f"{', '.join(save_functions) if save_functions else 'Nao identificada com confianca nos arquivos amostrados.'}\n\n"
            "Evidencia textual\n"
            f"{evidence_text}\n\n"
            "Veredito\n"
            f"{verdict}\n\n"
            "Observacao\n"
            "Este diagnostico foi gerado por leitura read-only de arquivos locais e cita evidencias pequenas; nao aplicou alteracoes no codigo-fonte.\n\n"
            "Solicitacao original\n"
            f"{prompt.strip()}\n"
        )

    def _collect_source_diagnosis_evidence(self, root: Path, terms: list[str]) -> list[dict[str, Any]]:
        ignored_dirs = {
            ".git",
            ".gradle",
            ".kotlin",
            ".idea",
            ".venv",
            "node_modules",
            "build",
            "dist",
            "__pycache__",
            "reports",
        }
        code_extensions = {".kt", ".kts", ".java", ".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".go", ".rs"}
        candidates: list[dict[str, Any]] = []
        for path in root.rglob("*"):
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            if set(relative.parts) & ignored_dirs:
                continue
            if not path.is_file() or path.suffix.casefold() not in code_extensions:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lowered = text.casefold()
            score = sum(lowered.count(term) for term in terms)
            name_lowered = path.name.casefold()
            if any(marker in name_lowered for marker in ("repository", "store", "storage", "persist", "data")):
                score += 8
            if score <= 0:
                continue
            snippets = self._evidence_snippets(text, terms)
            candidates.append(
                {
                    "relative_path": relative.as_posix(),
                    "score": score,
                    "text": text,
                    "snippets": snippets,
                }
            )
        candidates.sort(key=lambda item: (item["score"], item["relative_path"]), reverse=True)
        return candidates[:8]

    def _evidence_snippets(self, text: str, terms: list[str]) -> list[dict[str, Any]]:
        matches: list[tuple[int, int, str]] = []
        priority_markers = {
            "fun load": 12,
            "fun save": 10,
            "fun export": 10,
            "writeatomically": 10,
            "writestring": 8,
            "loadedfromdisk = true": 8,
            "readstring": 7,
            "exists()": 6,
            "loadedfromdisk": 5,
            "demodata": 3,
        }
        for index, line in enumerate(text.splitlines(), start=1):
            lowered = line.casefold()
            if not any(term in lowered for term in terms):
                continue
            clean_line = re.sub(r"\s+", " ", line).strip()
            if not clean_line:
                continue
            if clean_line.startswith(("import ", "package ")):
                continue
            score = sum(weight for marker, weight in priority_markers.items() if marker in lowered)
            score += sum(1 for term in terms if term in lowered)
            matches.append((score, index, clean_line[:220]))
        selected = sorted(sorted(matches, key=lambda item: (-item[0], item[1]))[:8], key=lambda item: item[1])
        return [{"line": index, "text": clean_line} for _, index, clean_line in selected]

    def _function_names_from_evidence(self, evidence: list[dict[str, Any]], keywords: tuple[str, ...]) -> list[str]:
        names: list[str] = []
        production_items = [item for item in evidence if "/test/" not in str(item.get("relative_path", "")).casefold()]
        search_items = (production_items[:1] if production_items else evidence[:1])
        for item in search_items:
            for match in re.finditer(r"\bfun\s+([A-Za-z0-9_]+)\s*\(", item.get("text", "")):
                name = match.group(1)
                if any(keyword in name.casefold() for keyword in keywords) and name not in names:
                    names.append(name)
        return names[:8]

    def _persistence_verdict(self, evidence: list[dict[str, Any]]) -> str:
        combined = "\n".join(str(item.get("text", "")) for item in evidence).casefold()
        has_disk_load = any(marker in combined for marker in ("readstring", "read_text", "readbytes", "exists()", "loadedfromdisk = true", "load():"))
        has_write = any(marker in combined for marker in ("writestring", "writeatomically", "write_text", "writebytes", "fun save", "fun export"))
        has_demo_fallback = any(marker in combined for marker in ("demodata", "demo data", "fallback", "loadedfromdisk = false"))
        if has_disk_load and has_write:
            return "persistence_real" if has_demo_fallback else "persistence_real"
        if has_demo_fallback and not has_write:
            return "persistence_fake_demo_only"
        return "persistence_partial"

    def _render_source_evidence(self, evidence: list[dict[str, Any]]) -> str:
        if not evidence:
            return "- Nenhuma evidencia textual localizada nos arquivos de codigo amostrados."
        lines: list[str] = []
        for item in evidence[:5]:
            lines.append(f"- {item['relative_path']} (score {item['score']})")
            for snippet in item.get("snippets", [])[:5]:
                lines.append(f"  - L{snippet['line']}: {snippet['text']}")
        return "\n".join(lines)

    def extract_requested_content(self, prompt: str) -> str | None:
        quoted_patterns = [
            r"(?:conte[úu]do|texto|contendo|com\s+o\s+texto|with\s+content)\s*[:=]?\s*[\"']([^\"']+)[\"']",
            r"(?:conte[úu]do|texto|contendo|com\s+o\s+texto|with\s+content)\s*[:=]?\s*`([^`]+)`",
        ]
        for pattern in quoted_patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if content:
                    return content
        fenced = re.findall(r"```(?:[A-Za-z0-9_-]+)?\s*(.*?)```", prompt, flags=re.DOTALL)
        if fenced:
            content = fenced[-1].strip()
            if content:
                return content
        return None

    def workspace_summary(self, workspace_context: str | None) -> dict[str, Any] | None:
        if not workspace_context:
            return None
        root = Path(workspace_context)
        try:
            resolved = root.resolve()
        except Exception:
            return None
        if not resolved.exists() or not resolved.is_dir():
            return None
        ignored_dirs = {
            ".git",
            ".gradle",
            ".kotlin",
            ".idea",
            ".venv",
            "node_modules",
            "build",
            "dist",
            "__pycache__",
        }
        max_files = 160
        files: list[Path] = []
        directories: set[str] = set()
        for item in resolved.rglob("*"):
            try:
                relative = item.relative_to(resolved)
            except ValueError:
                continue
            parts = set(relative.parts)
            if parts & ignored_dirs:
                continue
            if item.is_dir():
                if len(relative.parts) == 1:
                    directories.add(relative.as_posix())
                continue
            if item.is_file():
                files.append(relative)
                if len(files) >= max_files:
                    break
        manifests = [
            name
            for name in (
                "README.md",
                "android",
                "settings.gradle.kts",
                "settings.gradle",
                "build.gradle.kts",
                "build.gradle",
                "package.json",
                "package-lock.json",
                "pnpm-lock.yaml",
                "yarn.lock",
                "bun.lockb",
                "pyproject.toml",
                "requirements.txt",
                "Cargo.toml",
            )
            if (resolved / name).exists()
        ]
        extensions: dict[str, int] = {}
        for file in files:
            suffix = file.suffix.lower() or "[sem_extensao]"
            extensions[suffix] = extensions.get(suffix, 0) + 1
        signals = self._workspace_signals(resolved, files, manifests)
        return {
            "root": str(resolved),
            "top_directories": sorted(directories)[:24],
            "manifests": manifests,
            "sample_files": [file.as_posix() for file in files[:40]],
            "file_count_sampled": len(files),
            "extensions": dict(sorted(extensions.items(), key=lambda item: (-item[1], item[0]))[:16]),
            "signals": signals,
            "package_json": self._package_json_summary(resolved),
        }

    def _workspace_signals(self, root: Path, files: list[Path], manifests: list[str]) -> list[str]:
        signals: list[str] = []
        manifest_set = set(manifests)
        suffixes = {file.suffix.lower() for file in files}
        paths = {file.as_posix().casefold() for file in files}
        if {"settings.gradle.kts", "settings.gradle", "build.gradle.kts", "build.gradle"} & manifest_set:
            signals.append("Projeto Gradle detectado por arquivos de build.")
        if ".kt" in suffixes or any(path.startswith("app/src/main/java") for path in paths):
            signals.append("Codigo Kotlin/Android detectado na arvore de fontes.")
        if "package.json" in manifest_set:
            signals.append("Projeto JavaScript/Node detectado por package.json.")
            package = self._package_json_summary(root)
            deps = set(package.get("dependencies", [])) | set(package.get("dev_dependencies", []))
            deps |= set(package.get("all_dependencies", [])) | set(package.get("all_dev_dependencies", []))
            if any(name in deps for name in {"react-native", "expo"}):
                signals.append("Runtime React Native/Expo detectado por dependencias do package.json.")
            if "react" in deps:
                signals.append("Dependencia React detectada.")
        if "pyproject.toml" in manifest_set or "requirements.txt" in manifest_set:
            signals.append("Projeto Python detectado por manifestos.")
        if any("androidmanifest.xml" in path for path in paths):
            signals.append("Manifest Android encontrado.")
        if "android" in manifest_set or any(path.startswith("android/") for path in paths):
            signals.append("Diretorio Android detectado na raiz ou na arvore amostrada.")
        if (root / "README.md").exists():
            signals.append("README disponivel para contexto inicial.")
        return signals or ["Estrutura de projeto detectada por inventario de arquivos."]

    def _package_json_summary(self, root: Path) -> dict[str, Any]:
        package_paths = self._package_json_paths(root)
        if not package_paths:
            return {}
        root_summary = self._read_package_json(package_paths[0])
        all_dependencies: set[str] = set(root_summary.get("dependencies", []))
        all_dev_dependencies: set[str] = set(root_summary.get("dev_dependencies", []))
        nested_scripts: dict[str, dict[str, str]] = {}
        package_files: list[str] = []
        for path in package_paths:
            summary = self._read_package_json(path)
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                relative = path.name
            package_files.append(relative)
            all_dependencies.update(str(item) for item in summary.get("dependencies", []))
            all_dev_dependencies.update(str(item) for item in summary.get("dev_dependencies", []))
            scripts = summary.get("scripts") if isinstance(summary.get("scripts"), dict) else {}
            if scripts:
                nested_scripts[relative] = scripts
        return {
            **root_summary,
            "package_files": package_files,
            "all_dependencies": sorted(all_dependencies),
            "all_dev_dependencies": sorted(all_dev_dependencies),
            "nested_scripts": nested_scripts,
        }

    def _package_json_paths(self, root: Path) -> list[Path]:
        ignored = {".git", ".gradle", ".kotlin", ".idea", ".venv", "node_modules", "build", "dist", "__pycache__"}
        paths: list[Path] = []
        root_package = root / "package.json"
        if root_package.exists():
            paths.append(root_package)
        for path in root.rglob("package.json"):
            if path == root_package:
                continue
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            if set(part.casefold() for part in relative.parts) & ignored:
                continue
            paths.append(path)
            if len(paths) >= 16:
                break
        return paths

    def _read_package_json(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError):
            return {"parse_error": True}
        dependencies = data.get("dependencies") if isinstance(data.get("dependencies"), dict) else {}
        dev_dependencies = data.get("devDependencies") if isinstance(data.get("devDependencies"), dict) else {}
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        return {
            "name": str(data.get("name") or ""),
            "scripts": {str(key): str(value) for key, value in scripts.items()},
            "dependencies": sorted(str(key) for key in dependencies.keys()),
            "dev_dependencies": sorted(str(key) for key in dev_dependencies.keys()),
        }

    def report_from_workspace_summary(self, prompt: str, summary: dict[str, Any]) -> str:
        directories = summary.get("top_directories") or []
        manifests = summary.get("manifests") or []
        sample_files = summary.get("sample_files") or []
        extensions = summary.get("extensions") or {}
        signals = summary.get("signals") or []
        package = summary.get("package_json") if isinstance(summary.get("package_json"), dict) else {}
        root = Path(str(summary.get("root") or "."))
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        requested_status = self.extract_requested_status(prompt) or "completed"
        checklist = self._requested_report_items(prompt)
        checklist_lines = self._render_requested_report_checklist(prompt, root, summary, checklist)
        build_scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        nested_scripts = package.get("nested_scripts") if isinstance(package.get("nested_scripts"), dict) else {}
        script_lines = self._render_script_lines(build_scripts, nested_scripts)
        package_manager = self._package_manager_from_summary(manifests)
        suggestions = [
            "Rodar validacao/build do projeto pelo fluxo governado antes de qualquer alteracao.",
            "Revisar manifests e arquivos de configuracao para confirmar compatibilidade de ambiente.",
            "Manter alteracoes futuras em patch/preview com validacao posterior.",
        ]
        if any(str(signal).casefold().find("gradle") >= 0 for signal in signals):
            suggestions.append("Validar wrapper Gradle, versoes de plugins e local.properties antes de build.")
        if any(str(signal).casefold().find("android") >= 0 for signal in signals):
            suggestions.append("Conferir Manifest, Activity principal e recursos Android antes de empacotar APK.")
        return (
            "Relatorio solicitado\n\n"
            "Titulo\n"
            "Relatorio de workspace governado\n\n"
            "Data\n"
            f"{generated_at}\n\n"
            "Workspace\n"
            f"{summary.get('root')}\n\n"
            "Status\n"
            f"{requested_status}\n\n"
            "Resumo\n"
            "Foi realizado um inventario leve e governado do diretorio informado para produzir um resumo textual sem aplicar alteracoes no codigo-fonte.\n\n"
            "Projeto analisado\n"
            f"- Raiz: {summary.get('root')}\n"
            f"- Arquivos amostrados: {summary.get('file_count_sampled')}\n"
            f"- Diretorios principais: {', '.join(directories) if directories else 'nenhum diretorio principal listado'}\n"
            f"- Manifestos/configuracoes encontrados: {', '.join(manifests) if manifests else 'nenhum manifesto conhecido encontrado'}\n"
            f"- Package manager provavel: {package_manager}\n"
            f"- Extensoes mais comuns: {', '.join(f'{key}={value}' for key, value in extensions.items()) if extensions else 'sem extensoes amostradas'}\n\n"
            "Funcionalidades/estrutura inferida\n"
            + "".join(f"- {signal}\n" for signal in signals)
            + "\nComandos declarados\n"
            + ("".join(f"- {line}\n" for line in script_lines) if script_lines else "- Nenhum script de package.json identificado.\n")
            + "\nChecklist solicitado\n"
            + checklist_lines
            + "\nSugestoes\n"
            + "".join(f"- {suggestion}\n" for suggestion in suggestions)
            + "\nFontes consultadas\n"
            + "".join(f"- {item}\n" for item in sample_files[:24])
            + "\nObservacao\n"
            "Este arquivo foi criado pelo fluxo de ferramentas governadas, com workspace e policy avaliados antes da escrita. "
            "A analise e baseada no inventario local disponivel; uma revisao profunda deve executar leitura dirigida, build/testes e validacao especifica do projeto.\n\n"
            "Solicitacao original\n"
            f"{prompt.strip()}\n"
        )

    def _package_manager_from_summary(self, manifests: list[str]) -> str:
        if "pnpm-lock.yaml" in manifests:
            return "pnpm"
        if "yarn.lock" in manifests:
            return "yarn"
        if "package-lock.json" in manifests:
            return "npm"
        if "bun.lockb" in manifests:
            return "bun"
        if "package.json" in manifests:
            return "npm/pnpm/yarn nao confirmado"
        return "nao identificado"

    def _requested_report_items(self, prompt: str) -> list[str]:
        marker = re.search(r"(?:relat[óo]rio\s+deve\s+conter|deve\s+conter|inclua)\s*:?", prompt, flags=re.IGNORECASE)
        if not marker:
            return []
        tail = prompt[marker.end():]
        items: list[str] = []
        for line in tail.splitlines():
            stripped = line.strip()
            if not stripped:
                if items:
                    break
                continue
            if stripped.lower().startswith(("valide ", "esperado", "regras", "nao ", "não ")):
                break
            bullet = re.match(r"^[*\-]\s+(.+)", stripped)
            if bullet:
                value = re.sub(r"\s+", " ", bullet.group(1)).strip(" ;.")
                if value:
                    items.append(value)
                continue
            if items and not stripped.startswith(("*", "-")):
                break
        return items[:24]

    def _render_requested_report_checklist(self, prompt: str, root: Path, summary: dict[str, Any], items: list[str]) -> str:
        if not items:
            return "- Nenhum checklist explicito foi extraido do prompt.\n\n"
        lines: list[str] = []
        for item in items:
            lines.append(f"- {item}: {self._answer_requested_report_item(item, prompt, root, summary)}")
        return "\n".join(lines) + "\n\n"

    def _answer_requested_report_item(self, item: str, prompt: str, root: Path, summary: dict[str, Any]) -> str:
        lowered = item.casefold()
        manifests = set(str(value) for value in summary.get("manifests") or [])
        signals = [str(value) for value in summary.get("signals") or []]
        package = summary.get("package_json") if isinstance(summary.get("package_json"), dict) else {}
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        nested_scripts = package.get("nested_scripts") if isinstance(package.get("nested_scripts"), dict) else {}
        script_lines = self._render_script_lines(scripts, nested_scripts)
        sample_files = {str(value).casefold() for value in summary.get("sample_files") or []}
        deps = set(str(value) for value in package.get("all_dependencies", []) or []) | set(str(value) for value in package.get("all_dev_dependencies", []) or [])
        has_react_native = bool({"react-native", "expo"} & deps)
        has_android = "android" in {str(value).casefold() for value in summary.get("manifests") or []} or any(path.startswith("android/") for path in sample_files)
        has_bundle = "android/app/src/main/assets/index.android.bundle" in sample_files
        has_bundle_script = any("bundle" in str(value).casefold() or "bundle" in str(key).casefold() for key, value in scripts.items())
        has_bundle_script = has_bundle_script or any(
            "bundle" in str(name).casefold() or "bundle" in str(value).casefold()
            for group in nested_scripts.values()
            if isinstance(group, dict)
            for name, value in group.items()
        )
        has_gradle_config = has_android or any("gradle" in path for path in sample_files)
        has_build_script = any(str(name).casefold() in {"build", "android"} or "assemble" in str(value).casefold() for name, value in scripts.items())
        has_build_script = has_build_script or any(
            str(name).casefold() in {"build", "android"} or "assemble" in str(value).casefold()
            for group in nested_scripts.values()
            if isinstance(group, dict)
            for name, value in group.items()
        )
        if "stack" in lowered or "framework" in lowered:
            return "; ".join(signals) if signals else "Nao identificado com confianca pelo inventario."
        if "veredito" in lowered:
            if has_react_native and not has_bundle:
                return "bundle_missing"
            if not has_android and has_react_native:
                return "project_incomplete"
            if not has_build_script:
                return "dependency_missing"
            return "unknown"
        if "react native" in lowered or "expo" in lowered or "android nativo" in lowered:
            if has_react_native:
                return "React Native/Expo detectado por dependencias em package.json."
            if has_android:
                return "Android nativo/Gradle detectado sem dependencia React Native confirmada."
            return "Nao confirmado; o inventario nao encontrou sinais suficientes de React Native, Expo ou Android nativo."
        if "package manager" in lowered or "gerenciador" in lowered:
            return self._package_manager_from_summary(list(manifests))
        if "debug" in lowered or "release" in lowered:
            return "Nao determinado pelo inventario estatico; requer inspecao de build variant/APK ou logs de build."
        if "metro" in lowered:
            return "Possivel dependencia de Metro se o APK for debug e nao houver bundle empacotado; confirmar em build.gradle/scripts."
        if "gradle" in lowered:
            return "configuracao Gradle detectada" if has_gradle_config else "configuracao Gradle nao detectada no inventario estatico"
        if "bundle" in lowered and "script" not in lowered:
            return "ausente (`android/app/src/main/assets/index.android.bundle`)" if not has_bundle else "presente (`android/app/src/main/assets/index.android.bundle`)"
        if "script de bundle" in lowered:
            return "script de bundle identificado" if has_bundle_script else "nenhum script de bundle identificado nos package.json amostrados"
        if "apk offline" in lowered:
            return "comando candidato identificado" if has_build_script else "nenhum comando claro para APK offline identificado"
        if "ferramentas" in lowered or "dependencias" in lowered:
            tools = [self._package_manager_from_summary(list(manifests))]
            if has_react_native:
                tools.extend(["Node.js", "React Native/Expo tooling"])
            if has_android or has_react_native:
                tools.extend(["JDK", "Android SDK/Gradle"])
            return ", ".join(dict.fromkeys(item for item in tools if item and item != "nao identificado"))
        if "raiz" in lowered or "root cause" in lowered or ("problema" in lowered and "provavel" in lowered):
            return self._probable_cause_from_prompt_and_summary(prompt, summary)
        if "estrategia" in lowered or "estratégia" in lowered or "strategy" in lowered:
            return self._minimal_strategy_from_summary(prompt, summary)
        if "arquivos candidatos" in lowered or "candidate files" in lowered or "files to change" in lowered:
            return self._candidate_files_from_summary(summary)
        if "validation plan" in lowered or "plano de validacao" in lowered or "plano de validação" in lowered:
            return self._validation_plan_from_summary(prompt, summary)
        if "rollback plan" in lowered or "plano de rollback" in lowered or "plano de reversao" in lowered or "plano de reversão" in lowered:
            return self._rollback_plan_from_summary(summary)
        if "approval_required" in lowered or "approval required" in lowered or "precisa de approval" in lowered:
            return "true para qualquer patch/aplicacao real; false apenas para diagnostico ou plano read-only."
        if "criterio de sucesso" in lowered or "critério de sucesso" in lowered or "success criteria" in lowered:
            return self._success_criteria_from_summary(prompt, summary)
        if "plano" in lowered:
            return "1. confirmar stack; 2. verificar bundle/assets; 3. criar patch minimo; 4. executar build governado; 5. validar APK/evidencias."
        if "comando" in lowered or "build" in lowered:
            if script_lines:
                return "; ".join(script_lines)
            return "Nenhum script de build identificado no package.json amostrado."
        if "causa" in lowered:
            return self._probable_cause_from_prompt_and_summary(prompt, summary)
        if "risco" in lowered:
            return "Validar build/testes antes de alterar; confirmar empacotamento de assets e dependencias; evitar declarar sucesso sem APK/artefato verificavel."
        if "proxima" in lowered or "próxima" in lowered or "acao" in lowered or "ação" in lowered:
            return "Executar diagnostico operacional com leitura dirigida dos manifests/build scripts e validar bundle/assets antes de patch."
        if "proximo" in lowered or "passo" in lowered or "next step" in lowered:
            return "Executar diagnostico operacional com leitura dirigida dos manifests/build scripts e validar bundle/assets antes de patch."
        path_status = self._requested_path_status(item, root, sample_files)
        if path_status:
            return path_status
        return "Item registrado para revisao; nao houve evidencia especifica suficiente no inventario leve."

    def _minimal_strategy_from_summary(self, prompt: str, summary: dict[str, Any]) -> str:
        cause = self._probable_cause_from_prompt_and_summary(prompt, summary)
        sample_files = {str(value).casefold() for value in summary.get("sample_files") or []}
        package = summary.get("package_json") if isinstance(summary.get("package_json"), dict) else {}
        deps = set(str(value) for value in package.get("all_dependencies", []) or []) | set(str(value) for value in package.get("all_dev_dependencies", []) or [])
        has_react_native = bool({"react-native", "expo"} & deps)
        has_mobile_build_script = any("artifacts/mobile/scripts/build.js" == item for item in sample_files)
        if "bundle" in cause.casefold() or has_react_native:
            steps = [
                "confirmar se o alvo de build e debug/offline ou release",
                "usar scripts/manifests existentes antes de criar estrutura nova",
                "garantir que o bundle/assets sejam produzidos ou que o build use Metro conscientemente",
                "validar o APK gerado em ambiente Android antes de declarar sucesso",
            ]
            if has_mobile_build_script:
                steps.insert(1, "inspecionar e ajustar o script de build mobile existente, se necessario")
            return "; ".join(steps) + "."
        return "corrigir apenas a menor lacuna comprovada pelo diagnostico, preservando a estrutura existente e validando antes de concluir."

    def _candidate_files_from_summary(self, summary: dict[str, Any]) -> str:
        sample_files = [str(value) for value in summary.get("sample_files") or []]
        preferred_markers = (
            "package.json",
            "eas.json",
            "build.js",
            "android-debug-build.yml",
            "app.json",
            "app.config",
            "metro.config",
            "babel.config",
            "gradle",
        )
        candidates: list[str] = []
        for path in sample_files:
            lowered = path.casefold()
            if any(marker in lowered for marker in preferred_markers):
                candidates.append(path)
        if not candidates:
            candidates = sample_files[:8]
        return "; ".join(dict.fromkeys(candidates[:12])) if candidates else "Nenhum arquivo candidato identificado pelo inventario leve."

    def _validation_plan_from_summary(self, prompt: str, summary: dict[str, Any]) -> str:
        package = summary.get("package_json") if isinstance(summary.get("package_json"), dict) else {}
        scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
        nested_scripts = package.get("nested_scripts") if isinstance(package.get("nested_scripts"), dict) else {}
        script_lines = self._render_script_lines(scripts, nested_scripts)
        validation_steps = ["executar typecheck/test/build disponiveis pelo fluxo governado"]
        if script_lines:
            validation_steps.append("priorizar comandos declarados no package.json em vez de comandos inventados")
        if "apk" in prompt.casefold() or "android" in prompt.casefold():
            validation_steps.extend([
                "gerar APK debug/offline quando o projeto oferecer comando suportado",
                "verificar existencia do APK/artifact final",
                "instalar ou inspecionar o APK para confirmar ausencia do erro reportado",
            ])
        return "; ".join(validation_steps) + "."

    def _rollback_plan_from_summary(self, summary: dict[str, Any]) -> str:
        candidates = self._candidate_files_from_summary(summary)
        if candidates.startswith("Nenhum"):
            return "registrar patch preview antes de aplicar e reverter integralmente o diff aprovado se a validacao falhar."
        return f"manter patch preview com diff dos arquivos candidatos ({candidates}); se a validacao falhar, reverter somente esses diffs e preservar relatorios/evidencias."

    def _success_criteria_from_summary(self, prompt: str, summary: dict[str, Any]) -> str:
        criteria = ["patch aplicado apenas apos approval quando houver escrita", "validacao governada concluida sem falha"]
        lowered = prompt.casefold()
        if "apk" in lowered or "android" in lowered:
            criteria.extend(["APK debug/offline gerado como artifact verificavel", "erro 'Unable to load script' ausente na validacao Android"])
        if "bundle" in lowered:
            criteria.append("bundle/assets JS presentes ou dependencia de Metro explicitamente documentada")
        return "; ".join(criteria) + "."

    def _requested_path_status(self, item: str, root: Path, sample_files: set[str]) -> str | None:
        candidates = re.findall(r"(?i)([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/?|[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,12})", item.replace("\\", "/"))
        ignored = {
            "presenca",
            "ausencia",
            "presenca/ausencia",
            "presence",
            "absence",
            "presence/absence",
            "package",
            "manager",
            "detectado",
            "arquivos",
            "principais",
        }
        for raw in candidates:
            value = raw.strip(" .,:;")
            if not value or value.casefold() in ignored:
                continue
            if "/" not in value and "." not in value and not value.endswith("/"):
                continue
            parts = [part for part in value.split("/") if part]
            if len(parts) > 1 and all("." in part for part in parts):
                present = any((root / part).exists() or part.casefold() in sample_files for part in parts)
                return f"{'presente' if present else 'ausente'} (`{value}`)"
            path = root / value.rstrip("/")
            exists = path.exists() or value.casefold() in sample_files
            return f"{'presente' if exists else 'ausente'} (`{value}`)"
        return None

    def _probable_cause_from_prompt_and_summary(self, prompt: str, summary: dict[str, Any]) -> str:
        lowered_prompt = prompt.casefold()
        sample_files = {str(value).casefold() for value in summary.get("sample_files") or []}
        manifests = {str(value).casefold() for value in summary.get("manifests") or []}
        has_android = "android" in manifests or any(path.startswith("android/") for path in sample_files)
        has_bundle = "android/app/src/main/assets/index.android.bundle" in sample_files
        if "unable to load script" in lowered_prompt and has_android and not has_bundle:
            return "O erro observado e compativel com bundle JS Android ausente ou nao empacotado; requer diagnostico operacional antes de patch."
        if "unable to load script" in lowered_prompt and not has_android:
            return "O erro observado sugere runtime React Native, mas o inventario leve nao encontrou diretorio android na raiz amostrada; confirmar estrutura gerada/artifacts."
        if "unable to load script" in lowered_prompt:
            return "O erro observado requer verificar modo debug/release, Metro e empacotamento de bundle/assets."
        return "Causa provavel nao determinada pelo inventario leve."

    def _render_script_lines(self, scripts: dict[str, str], nested_scripts: dict[str, Any]) -> list[str]:
        lines = [f"{name}: `{value}`" for name, value in scripts.items()]
        for package_file, group in nested_scripts.items():
            if not isinstance(group, dict):
                continue
            for name, value in group.items():
                entry = f"{package_file} {name}: `{value}`"
                if entry not in lines:
                    lines.append(entry)
        return lines[:16]

    def extract_requested_status(self, prompt: str) -> str | None:
        match = re.search(r"\bstatus\s+([A-Za-z0-9_.:-]{3,80})", prompt, flags=re.IGNORECASE)
        if not match:
            return None
        value = match.group(1).strip(" .,:;")
        return value or None

    def content_for_modified_file(self, prompt: str, original: str, content_hint: str = "") -> str:
        explicit_content = self.extract_requested_content(prompt)
        if explicit_content is not None:
            addition = explicit_content.strip()
        else:
            clean_hint = content_hint.strip()
            addition = clean_hint if clean_hint and not self.looks_like_failed_content(clean_hint) else self._generic_modify_addition(prompt)
        separator = "" if original.endswith("\n") else "\n"
        return f"{original}{separator}\n{addition.rstrip()}\n"

    def _generic_modify_addition(self, prompt: str) -> str:
        section = self.extract_requested_section(prompt)
        body = self.extract_requested_section_body(prompt) or self.extract_requested_short_phrase(prompt) or "Atualizacao governada solicitada pelo usuario."
        if section:
            return f"## {section}\n\n{body}"
        return body

    def extract_requested_section(self, prompt: str) -> str | None:
        named_match = re.search(
            r"(?:secao|seção|section)\s+(?:chamada|chamado|nomeada|nomeado|intitulada|intitulado|called|named|titled)\s+[`\"']?([^`\"'.\n]+?)(?:[`\"']|\s+com\b|[.;,]|$)",
            prompt,
            flags=re.IGNORECASE,
        )
        if named_match:
            value = re.sub(r"\s+", " ", named_match.group(1)).strip(" :-")
            if value:
                return value[:120]
        patterns = [
            r"(?:se[cç][aã]o|section)\s+[`\"']?([^`\"'.\n]+?)(?:\s+com\b|[.;,]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
                if value:
                    return value[:120]
        return None

    def extract_requested_section_body(self, prompt: str) -> str | None:
        patterns = [
            r"(?:a\s+)?(?:secao|seção|section)\s+(?:deve|devera|deveria|should)\s+(?:resumir|descrever|explicar|mencionar|mention|describe|explain)\s*,?\s*(?:em\s+poucas\s+linhas,?\s*)?(?:que|:)\s+(.+?)(?:\n\n|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE | re.DOTALL)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" .:-")
                if value:
                    return value[:500]
        return None

    def extract_requested_short_phrase(self, prompt: str) -> str | None:
        patterns = [
            r"(?:com|contendo|incluindo)\s+(?:uma\s+)?(?:frase\s+curta|texto)\s*[:=]?\s*[`\"']?([^`\"'.\n]+)[`\"']?",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
                if value:
                    return value[:240]
        return None

    def looks_like_failed_content(self, text: str) -> bool:
        lowered = text.casefold()
        failure_markers = (
            "não consegui",
            "nao consegui",
            "nÃ£o consegui",
            "não pude",
            "nao pude",
            "nÃ£o pude",
            "foi rejeitad",
            "foi bloquead",
            "falhou",
            "failed",
            "blocked",
        )
        return any(marker in lowered for marker in failure_markers)
