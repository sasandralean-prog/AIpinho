from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.pinhoforge_bridge.pinhoforge_android_workbench_provider import PinhoForgeAndroidWorkbenchProvider
from aipinho.services.pinhoforge_bridge.pinhoforge_conversion_provider import PinhoForgeConversionProvider
from aipinho.services.pinhoforge_bridge.pinhoforge_hardware_profiler_provider import PinhoForgeHardwareProfilerProvider
from aipinho.services.pinhoforge_bridge.pinhoforge_media_3d_provider import PinhoForge3DProvider, PinhoForgeImageProvider
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(slots=True)
class BridgeWorkflowRecipe:
    recipe_id: str
    provider_id: str
    tool_name: str
    capability_id: str
    operation: str
    keywords: list[str]
    categories: list[str]
    risk_level: str
    source_scope: str
    requires_preview: bool
    requires_approval: bool
    side_effects_expected: bool
    expected_outputs: list[str]
    default_input: dict[str, Any]


class PinhoForgeWorkflowProviderRegistry:
    def __init__(self, config_path=None) -> None:
        self.config_path = config_path or PATHS.config_root / "autopilot" / "pinhoforge_workflow_registry.yaml"
        self._config = load_yaml_file(self.config_path, critical=False, root=PATHS.config_root) if self.config_path.exists() else {}
        self._recipes = [self._recipe_from_row(row) for row in self._config.get("recipes", [])]

    def default_source_scope(self) -> str:
        return str(self._config.get("default_source_scope") or "sandbox")

    def bridge_readiness(self) -> dict[str, Any]:
        hardware = PinhoForgeHardwareProfilerProvider().handle(
            request=self._hardware_request("get_readiness_summary")
        )
        conversion = PinhoForgeConversionProvider().list_capabilities("bridge_workflow_conversion")
        image = PinhoForgeImageProvider().list_capabilities("bridge_workflow_image")
        scene3d = PinhoForge3DProvider().list_capabilities("bridge_workflow_3d")
        android = PinhoForgeAndroidWorkbenchProvider().handle(
            request=self._android_request("environment_readiness")
        )
        return {
            "hardware": {"status": hardware.status, "warnings": hardware.warnings, "readiness_summary": hardware.readiness_summary.model_dump() if hardware.readiness_summary else {}},
            "conversion": {"status": conversion.status, "warnings": conversion.logs_sanitized, "capabilities": conversion.capabilities},
            "image": {"status": image.status, "warnings": image.warnings, "capabilities": image.capabilities},
            "media_3d": {"status": scene3d.status, "warnings": scene3d.warnings, "capabilities": scene3d.capabilities},
            "android": {"status": android.status, "warnings": android.warnings, "environment_readiness": android.environment_readiness or {}},
        }

    def select_recipes(
        self,
        *,
        user_goal: str,
        requested_capabilities: list[str],
        workspace_ref: str | None,
        source_scope: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        lowered = user_goal.casefold()
        requested = {item for item in requested_capabilities if item}
        categories = {str(item).casefold() for item in metadata.get("bridge_categories", []) if str(item).strip()}
        explicit_tools = [str(item) for item in metadata.get("bridge_tools", []) if str(item).strip()]
        selected: list[BridgeWorkflowRecipe] = []
        if self._config.get("prepend_readiness_steps", True):
            readiness = self._find_recipe("bridge_readiness_summary")
            if readiness is not None:
                selected.append(readiness)
        for recipe in self._recipes:
            if recipe.recipe_id == "bridge_readiness_summary":
                continue
            if explicit_tools and recipe.tool_name in explicit_tools:
                selected.append(recipe)
                continue
            if recipe.capability_id in requested:
                selected.append(recipe)
                continue
            if categories.intersection({item.casefold() for item in recipe.categories}):
                selected.append(recipe)
                continue
            if any(keyword.casefold() in lowered for keyword in recipe.keywords):
                selected.append(recipe)
        if len(selected) == 1:
            fallback = self._find_recipe("bridge_command_search")
            if fallback is not None:
                selected.append(fallback)
        recipes = self._dedupe(selected)
        rendered = [
            self.render_recipe(
                recipe,
                user_goal=user_goal,
                workspace_ref=workspace_ref,
                source_scope=source_scope or self.default_source_scope(),
                metadata=metadata,
            )
            for recipe in recipes
        ]
        return {
            "recipes": rendered,
            "provider_readiness": self.bridge_readiness(),
            "selected_tools": [recipe["tool_name"] for recipe in rendered],
        }

    def render_recipe(
        self,
        recipe: BridgeWorkflowRecipe,
        *,
        user_goal: str,
        workspace_ref: str | None,
        source_scope: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        rendered_input = self._render_value(
            recipe.default_input,
            user_goal=user_goal,
            workspace_ref=workspace_ref,
            source_scope=source_scope,
            metadata=metadata,
        )
        if recipe.tool_name == "pinhoforge_terminal_execute" and not rendered_input.get("preview_id"):
            rendered_input = {**rendered_input, "preview_id": str(metadata.get("terminal_preview_id") or "")}
        return {
            "recipe_id": recipe.recipe_id,
            "provider_id": recipe.provider_id,
            "tool_name": recipe.tool_name,
            "capability_id": recipe.capability_id,
            "operation": recipe.operation,
            "risk_level": recipe.risk_level,
            "source_scope": source_scope if source_scope == "unknown" or recipe.source_scope == "registered_workspace" else recipe.source_scope,
            "requires_preview": recipe.requires_preview,
            "requires_approval": recipe.requires_approval,
            "side_effects_expected": recipe.side_effects_expected,
            "expected_outputs": list(recipe.expected_outputs),
            "input": rendered_input,
        }

    def _recipe_from_row(self, row: dict[str, Any]) -> BridgeWorkflowRecipe:
        return BridgeWorkflowRecipe(
            recipe_id=str(row.get("recipe_id")),
            provider_id=str(row.get("provider_id")),
            tool_name=str(row.get("tool_name")),
            capability_id=str(row.get("capability_id")),
            operation=str(row.get("operation")),
            keywords=[str(item) for item in row.get("keywords", [])],
            categories=[str(item) for item in row.get("categories", [])],
            risk_level=str(row.get("risk_level") or "low"),
            source_scope=str(row.get("source_scope") or self.default_source_scope()),
            requires_preview=bool(row.get("requires_preview", False)),
            requires_approval=bool(row.get("requires_approval", False)),
            side_effects_expected=bool(row.get("side_effects_expected", False)),
            expected_outputs=[str(item) for item in row.get("expected_outputs", [])],
            default_input=dict(row.get("default_input") or {}),
        )

    def _find_recipe(self, recipe_id: str) -> BridgeWorkflowRecipe | None:
        return next((recipe for recipe in self._recipes if recipe.recipe_id == recipe_id), None)

    def _dedupe(self, recipes: list[BridgeWorkflowRecipe]) -> list[BridgeWorkflowRecipe]:
        seen: set[str] = set()
        ordered: list[BridgeWorkflowRecipe] = []
        for recipe in recipes:
            if recipe.recipe_id in seen:
                continue
            seen.add(recipe.recipe_id)
            ordered.append(recipe)
        return ordered

    def _render_value(self, value: Any, *, user_goal: str, workspace_ref: str | None, source_scope: str, metadata: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return (
                value.replace("{user_goal}", user_goal)
                .replace("{workspace_ref}", workspace_ref or "")
                .replace("{source_scope}", source_scope)
            )
        if isinstance(value, list):
            return [self._render_value(item, user_goal=user_goal, workspace_ref=workspace_ref, source_scope=source_scope, metadata=metadata) for item in value]
        if isinstance(value, dict):
            return {
                key: self._render_value(item, user_goal=user_goal, workspace_ref=workspace_ref, source_scope=source_scope, metadata=metadata)
                for key, item in value.items()
            }
        return value

    def _hardware_request(self, operation: str):
        from aipinho.schemas.pinhoforge_bridge.hardware_profiler import PinhoForgeHardwareProfilerRequest

        return PinhoForgeHardwareProfilerRequest(operation=operation)

    def _android_request(self, operation: str):
        from aipinho.schemas.pinhoforge_bridge.android_workbench import PinhoForgeAndroidWorkbenchRequest

        return PinhoForgeAndroidWorkbenchRequest(operation=operation)
