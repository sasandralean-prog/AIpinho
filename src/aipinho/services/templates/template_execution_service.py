from __future__ import annotations

from typing import Callable

from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.templates import TemplateExecutionBundle, TemplateExecutionRequest, TemplateExecutionResult
from aipinho.services.sandbox.project_templates import (
    android_kotlin_simple_game_template,
    generic_files_template,
    python_simple_app_template,
    static_web_template,
)
from aipinho.services.templates.asset_placeholder_generator import AssetPlaceholderGenerator
from aipinho.services.templates.template_registry_service import TemplateRegistryService


class TemplateExecutionService:
    def __init__(
        self,
        *,
        registry: TemplateRegistryService | None = None,
        asset_generator: AssetPlaceholderGenerator | None = None,
    ) -> None:
        self.registry = registry or TemplateRegistryService()
        self.asset_generator = asset_generator or AssetPlaceholderGenerator()
        self._generators: dict[str, Callable[[TemplateExecutionRequest], dict[str, str]]] = {
            "android_kotlin_game": self._android_kotlin_game,
            "android_kotlin_app": self._android_kotlin_app,
            "python_cli": self._python_cli,
            "python_fastapi": self._python_fastapi,
            "static_web": self._static_web,
            "docs_pack": self._docs_pack,
            "mobile_component_demo": self._mobile_component_demo,
            "launcher_tool_demo": self._launcher_tool_demo,
            "generic_files": self._generic_files,
        }

    def render(self, request: TemplateExecutionRequest) -> TemplateExecutionBundle:
        manifest = self.registry.require(request.template_id)
        generator = self._generators.get(manifest.generator_key)
        if generator is None:
            result = TemplateExecutionResult(
                template_execution_id=request.template_execution_id,
                template_id=manifest.template_id,
                template_version=manifest.version,
                status="failed",
                project_root=request.project_name,
                errors=[f"unknown_generator:{manifest.generator_key}"],
                completed_at=utc_now_iso(),
            )
            return TemplateExecutionBundle(execution=result, files={})
        files = generator(request)
        assets = [path for path in files if "/res/drawable/" in path or path.startswith("assets/")]
        result = TemplateExecutionResult(
            template_execution_id=request.template_execution_id,
            template_id=manifest.template_id,
            template_version=manifest.version,
            status="completed",
            project_root=request.project_name,
            files_created=sorted(files.keys()),
            assets_created=sorted(assets),
            completed_at=utc_now_iso(),
            metadata_sanitized={
                "generator_key": manifest.generator_key,
                "required_files": manifest.required_files,
                "validation_profile": manifest.validation_profile,
            },
        )
        return TemplateExecutionBundle(execution=result, files=files)

    def _android_kotlin_game(self, request: TemplateExecutionRequest) -> dict[str, str]:
        project_slug = self._package_slug(request.project_name)
        package_name = f"br.com.aipinho.sandbox.{project_slug}"
        requested_assets = [str(item) for item in request.requested_assets]
        return android_kotlin_simple_game_template(
            project_name=request.project_name,
            package_name=package_name,
            character_asset=requested_assets[0] if requested_assets else "character",
            obstacle_asset=requested_assets[1] if len(requested_assets) > 1 else "obstacle",
        )

    def _android_kotlin_app(self, request: TemplateExecutionRequest) -> dict[str, str]:
        package_name = f"br.com.aipinho.sandbox.{self._package_slug(request.project_name)}"
        package_path = package_name.replace(".", "/")
        icon, _ = self.asset_generator.vector_xml(label="app_icon", color="#22d3ee", shape="circle", template_id=request.template_id)
        return {
            "settings.gradle.kts": f'pluginManagement {{ repositories {{ google(); mavenCentral(); gradlePluginPortal() }} }}\ndependencyResolutionManagement {{ repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories {{ google(); mavenCentral() }} }}\nrootProject.name = "{request.project_name}"\ninclude(":app")\n',
            "build.gradle.kts": 'plugins {\n    id("com.android.application") version "8.5.2" apply false\n    id("org.jetbrains.kotlin.android") version "1.9.24" apply false\n}\n',
            "app/build.gradle.kts": f'plugins {{ id("com.android.application"); id("org.jetbrains.kotlin.android") }}\n\nandroid {{ namespace = "{package_name}"; compileSdk = 35\n    defaultConfig {{ applicationId = "{package_name}"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "1.0" }}\n}}\n',
            "app/src/main/AndroidManifest.xml": f'<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application android:theme="@style/AppTheme" android:label="{request.project_name}"><activity android:name=".MainActivity" android:exported="true"><intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter></activity></application></manifest>\n',
            "app/src/main/res/values/styles.xml": '<resources><style name="AppTheme" parent="android:style/Theme.Material.NoActionBar"><item name="android:windowBackground">#05070d</item><item name="android:fontFamily">sans</item><item name="android:colorAccent">#22d3ee</item></style></resources>\n',
            "app/src/main/res/drawable/app_icon.xml": icon,
            f"app/src/main/java/{package_path}/MainActivity.kt": f"""package {package_name}

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

class MainActivity : Activity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        val view = TextView(this)
        view.text = "{request.project_name}\\nGenerated by AIpinho sandbox."
        view.textSize = 22f
        view.setTextColor(0xFF22D3EE.toInt())
        view.setBackgroundColor(0xFF05070D.toInt())
        view.setPadding(32, 32, 32, 32)
        setContentView(view)
    }}
}}
""",
            "README.md": f"# {request.project_name}\n\nMinimal Android Kotlin app generated from a declarative AIpinho template.\n",
        }

    def _python_cli(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return python_simple_app_template(project_name=request.project_name)

    def _python_fastapi(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return {
            "README.md": f"# {request.project_name}\n\nFastAPI service generated inside AIpinho sandbox.\n\n## Run\n\n```powershell\nuvicorn app.main:app --reload\n```\n",
            "requirements.txt": "fastapi\nuvicorn\n",
            "app/__init__.py": "",
            "app/main.py": 'from fastapi import FastAPI\n\napp = FastAPI(title="AIpinho Sandbox API")\n\n\n@app.get("/health")\ndef health() -> dict[str, str]:\n    return {"status": "ok"}\n',
            "tests/test_basic.py": 'from app.main import health\n\n\ndef test_health():\n    assert health()["status"] == "ok"\n',
        }

    def _static_web(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return static_web_template(project_name=request.project_name)

    def _docs_pack(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return {
            "README.md": f"# {request.project_name}\n\nDocumentation pack generated in the AIpinho sandbox.\n",
            "ARCHITECTURE.md": "# Architecture\n\nDescribe components, data flow, and constraints here.\n",
            "RUNBOOK.md": "# Runbook\n\nDocument setup, validation, rollback, and operational notes.\n",
            "TEST_PLAN.md": "# Test Plan\n\nList smoke, regression, and acceptance checks.\n",
            "CHANGELOG.md": "# Changelog\n\n## Unreleased\n\n- Initial generated documentation pack.\n",
        }

    def _mobile_component_demo(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return {
            "README.md": f"# {request.project_name}\n\nMobile component demo scaffold.\n",
            "components/ArtifactPanelDemo.kt": 'package demo\n\nclass ArtifactPanelDemo {\n    fun title(): String = "Artifacts"\n}\n',
            "components/TerminalPanelDemo.kt": 'package demo\n\nclass TerminalPanelDemo {\n    fun title(): String = "Terminal"\n}\n',
        }

    def _launcher_tool_demo(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return {
            "README.md": f"# {request.project_name}\n\nLauncher tool demo scaffold.\n",
            "config/tool.example.json": '{\n  "tool_id": "example_tool",\n  "enabled": true\n}\n',
            "scripts/status.ps1": "Write-Output 'status=ok'\n",
        }

    def _generic_files(self, request: TemplateExecutionRequest) -> dict[str, str]:
        return generic_files_template(project_name=request.project_name, user_goal=request.user_goal)

    def _package_slug(self, value: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
        return safe or "sandbox_project"
