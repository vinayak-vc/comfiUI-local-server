"""Workflow building service for ComfyUI execution."""

from typing import Any

from app.core.config import Settings
from app.schemas.comfy import GenerationMode, WorkflowRuntimeParameters
from app.workflows.injection import WorkflowParameterInjector
from app.workflows.template import WorkflowTemplate, WorkflowTemplateLoader


class WorkflowBuilder:
    """Loads reusable templates and applies runtime generation parameters."""

    def __init__(self, settings: Settings) -> None:
        self._loader: WorkflowTemplateLoader = WorkflowTemplateLoader(settings)
        self._injector: WorkflowParameterInjector = WorkflowParameterInjector()

    def build(
        self,
        mode: GenerationMode,
        parameters: WorkflowRuntimeParameters,
        workflow_name: str | None,
    ) -> dict[str, Any]:
        template: WorkflowTemplate = self._loader.load(mode, workflow_name)
        workflow: dict[str, Any] = template.clone_workflow()
        return self._injector.inject(workflow, parameters, template.parameter_map)
