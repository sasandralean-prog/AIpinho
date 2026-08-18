from __future__ import annotations

import re
from pathlib import Path

from aipinho.schemas.projects import CommandProfile, ProjectProfileCandidate, ValidationProfile, WorkspaceProfile
from aipinho.schemas.projects.project_profile import StackKind
from aipinho.services.projects.project_profile_secret_scanner import ProjectProfileSecretScanner


class ProjectProfileDetector:
    """Read-only project detector based on generic filesystem markers."""

    MARKERS: dict[str, set[str]] = {
        "android_gradle": {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradlew", "gradlew.bat"},
        "python": {"pyproject.toml", "requirements.txt", "setup.py", "pytest.ini"},
        "node": {"package.json", "tsconfig.json", "pnpm-lock.yaml", "package-lock.json", "yarn.lock"},
    }

    def detect(self, root_path: str, *, display_name: str | None = None) -> ProjectProfileCandidate:
        root = Path(root_path).expanduser().resolve()
        detected_files = self._detect_files(root)
        stack = self._stack(detected_files)
        confidence = self._confidence(stack, detected_files)
        project_id = self._slug(display_name or root.name)
        workspaces = self._workspaces(project_id, root)
        commands = self._commands(project_id, stack, detected_files)
        validation = self._validation(project_id, commands, stack)
        risks = [] if root.exists() else ["root_path_missing"]
        risks.extend(self._secret_risks(root))
        missing = [] if stack != "unknown" else ["stack_unknown_add_validation_commands"]
        return ProjectProfileCandidate(
            detected_stack=stack,
            confidence=confidence,
            root_path=str(root),
            detected_files=detected_files,
            suggested_workspaces=workspaces,
            suggested_commands=commands,
            suggested_validation_profile=validation,
            risks=risks,
            missing_info=missing,
            evidence_refs=[f"file:{item}" for item in detected_files[:20]],
        )

    def _secret_risks(self, root: Path) -> list[str]:
        if not root.exists() or not root.is_dir():
            return []
        scanner = ProjectProfileSecretScanner()
        scan_names = [".env", ".env.local", ".env.example", "appsettings.json", "secrets.json"]
        for name in scan_names:
            path = root / name
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:20000]
            except OSError:
                continue
            if scanner.scan({"file": name, "content": text}):
                return ["secret_risk_detected"]
        return []

    def _detect_files(self, root: Path) -> list[str]:
        if not root.exists() or not root.is_dir():
            return []
        candidates = [
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
            "gradlew",
            "gradlew.bat",
            "pyproject.toml",
            "requirements.txt",
            "setup.py",
            "pytest.ini",
            "package.json",
            "tsconfig.json",
            "pnpm-lock.yaml",
            "package-lock.json",
            "yarn.lock",
            "README.md",
            "src",
            "tests",
            "app",
            "backend",
            "mobile",
            "launcher",
            "docs",
            "reports",
            "config",
        ]
        return [item for item in candidates if (root / item).exists()]

    def _stack(self, files: list[str]) -> StackKind:
        has_android = bool(set(files) & self.MARKERS["android_gradle"])
        has_python = bool(set(files) & self.MARKERS["python"])
        has_node = bool(set(files) & self.MARKERS["node"])
        if sum([has_android, has_python, has_node]) > 1:
            return "mixed"
        if has_android:
            return "android_gradle"
        if has_python:
            return "python"
        if has_node:
            return "node"
        return "unknown"

    def _confidence(self, stack: StackKind, files: list[str]) -> float:
        if stack == "unknown":
            return 0.2 if files else 0.0
        marker_hits = len(set(files) & set().union(*self.MARKERS.values()))
        return min(0.95, 0.55 + marker_hits * 0.1)

    def _workspaces(self, project_id: str, root: Path) -> list[WorkspaceProfile]:
        return [
            WorkspaceProfile(
                workspace_id=f"{project_id}_source",
                project_id=project_id,
                role="source_readonly",
                path=str(root),
                display_name="Fonte read-only",
                access_policy="read_allowed",
                write_policy="write_denied",
                shell_policy="readonly_shell_only",
                exists=root.exists(),
                validation_status="ok" if root.exists() else "missing",
                evidence_refs=[f"path:{root}"],
            ),
            WorkspaceProfile(
                workspace_id=f"{project_id}_target",
                project_id=project_id,
                role="target_mutable",
                path=str(root),
                display_name="Workspace mutavel governado",
                access_policy="read_allowed",
                write_policy="governed_write",
                shell_policy="governed_shell",
                exists=root.exists(),
                validation_status="ok" if root.exists() else "missing",
                evidence_refs=[f"path:{root}"],
            ),
        ]

    def _commands(self, project_id: str, stack: StackKind, files: list[str]) -> list[CommandProfile]:
        commands: list[CommandProfile] = []
        if stack in {"android_gradle", "mixed"} and ("gradlew.bat" in files or "gradlew" in files):
            gradle = ".\\gradlew.bat" if "gradlew.bat" in files else "./gradlew"
            commands.extend(
                [
                    CommandProfile(command_id=f"{project_id}_assemble_debug", project_id=project_id, label="Assemble Debug", command=[gradle, "assembleDebug"], category="build", risk_level="medium", requires_approval=False, timeout_seconds=900, expected_outputs=["APK debug"]),
                    CommandProfile(command_id=f"{project_id}_test", project_id=project_id, label="Gradle Test", command=[gradle, "test"], category="test", risk_level="medium", requires_approval=False, timeout_seconds=900),
                ]
            )
        if stack in {"python", "mixed"}:
            commands.extend(
                [
                    CommandProfile(command_id=f"{project_id}_py_compile", project_id=project_id, label="Python compileall", command=["python", "-m", "compileall", "."], category="validate", risk_level="low", requires_approval=False, timeout_seconds=300),
                    CommandProfile(command_id=f"{project_id}_pytest", project_id=project_id, label="Pytest", command=["python", "-m", "pytest", "-q"], category="test", risk_level="medium", requires_approval=False, timeout_seconds=900),
                ]
            )
        if stack in {"node", "mixed"}:
            commands.extend(
                [
                    CommandProfile(command_id=f"{project_id}_npm_test", project_id=project_id, label="NPM Test", command=["npm", "test"], category="test", risk_level="medium", requires_approval=False, timeout_seconds=900),
                    CommandProfile(command_id=f"{project_id}_npm_build", project_id=project_id, label="NPM Build", command=["npm", "run", "build"], category="build", risk_level="medium", requires_approval=False, timeout_seconds=900),
                ]
            )
        if not commands:
            commands.append(CommandProfile(command_id=f"{project_id}_inspect", project_id=project_id, label="Read-only inspect", command=["inspect"], category="inspect", risk_level="low", requires_approval=False, timeout_seconds=120))
        return commands

    def _validation(self, project_id: str, commands: list[CommandProfile], stack: StackKind) -> ValidationProfile:
        command_ids = [item.command_id for item in commands]
        return ValidationProfile(
            validation_profile_id=f"{project_id}_validation",
            project_id=project_id,
            default_validation_sequence=command_ids[:2],
            quick_validation_sequence=command_ids[:1],
            full_validation_sequence=command_ids,
            smoke_validation_sequence=command_ids[:1],
            command_profiles=command_ids,
            required_evidence=["project_profile", "workspace_resolution"],
            validation_failure_policy="block_completion",
        )

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug or "project"
