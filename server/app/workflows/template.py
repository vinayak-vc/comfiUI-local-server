"""Workflow template loading for reusable ComfyUI graphs."""

import copy
import json
from pathlib import Path
from typing import Any

from app.comfy.exceptions import WorkflowTemplateError
from app.core.config import PROJECT_ROOT, Settings
from app.schemas.comfy import GenerationMode


class WorkflowTemplate:
    """Loaded ComfyUI workflow template and optional injection metadata."""

    def __init__(
        self,
        name: str,
        mode: GenerationMode,
        workflow: dict[str, Any],
        parameter_map: dict[str, Any],
    ) -> None:
        self.name: str = name
        self.mode: GenerationMode = mode
        self.workflow: dict[str, Any] = workflow
        self.parameter_map: dict[str, Any] = parameter_map

    def clone_workflow(self) -> dict[str, Any]:
        return copy.deepcopy(self.workflow)


class WorkflowTemplateLoader:
    """Loads JSON workflow templates from the configured workflow directory."""

    def __init__(self, settings: Settings) -> None:
        self._workflow_root: Path = settings.workflows_path

    def load(self, mode: GenerationMode, workflow_name: str | None) -> WorkflowTemplate:
        template_path: Path = self._resolve_template_path(mode, workflow_name)
        if not template_path.exists():
            template_path = self._resolve_legacy_template_path(template_path.name)
        if not template_path.exists():
            raise WorkflowTemplateError(f"Workflow template does not exist: {template_path}")

        try:
            raw_template: Any = json.loads(template_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise WorkflowTemplateError(f"Workflow template contains invalid JSON: {template_path}") from exc

        if not isinstance(raw_template, dict):
            raise WorkflowTemplateError("Workflow template root must be a JSON object.")

        workflow: dict[str, Any]
        parameter_map: dict[str, Any]

        if isinstance(raw_template.get("workflow"), dict):
            workflow = raw_template["workflow"]
            raw_parameter_map: Any = raw_template.get("parameter_map", {})
            parameter_map = raw_parameter_map if isinstance(raw_parameter_map, dict) else {}
        else:
            workflow = raw_template
            parameter_map = {}

        return WorkflowTemplate(
            name=template_path.stem,
            mode=mode,
            workflow=workflow,
            parameter_map=parameter_map,
        )

    def _resolve_template_path(self, mode: GenerationMode, workflow_name: str | None) -> Path:
        template_name: str = workflow_name if workflow_name is not None else mode.value
        template_path: Path = Path(template_name)
        if template_path.is_absolute() or ".." in template_path.parts:
            raise WorkflowTemplateError("Workflow template path is not allowed.")

        if not template_name.endswith(".json"):
            template_name = f"{template_name}.json"

        resolved_path: Path = (self._workflow_root / template_name).resolve()
        resolved_root: Path = self._workflow_root.resolve()
        if resolved_root not in resolved_path.parents and resolved_path != resolved_root:
            raise WorkflowTemplateError("Workflow template path escapes configured root.")
        return resolved_path

    def _resolve_legacy_template_path(self, template_filename: str) -> Path:
        legacy_root: Path = (PROJECT_ROOT / "workflow").resolve()
        resolved_path: Path = (legacy_root / template_filename).resolve()
        if legacy_root not in resolved_path.parents and resolved_path != legacy_root:
            raise WorkflowTemplateError("Workflow template path escapes configured root.")
        return resolved_path
