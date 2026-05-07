"""Workflow parameter injection tests."""

from typing import Any

import pytest

from app.comfy.exceptions import WorkflowTemplateError
from app.core.config import Settings
from app.schemas.comfy import GenerationMode, WorkflowRuntimeParameters
from app.workflows.injection import WorkflowParameterInjector
from app.workflows.template import WorkflowTemplateLoader


def test_injector_applies_standard_comfyui_node_conventions() -> None:
    workflow: dict[str, Any] = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ""},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ""},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "sampler_name": "euler",
                "steps": 20,
                "cfg": 7,
            },
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 512,
                "height": 512,
                "batch_size": 1,
            },
        },
    }
    parameters: WorkflowRuntimeParameters = WorkflowRuntimeParameters(
        prompt="cinematic city",
        negative_prompt="low quality",
        seed=123,
        sampler="dpmpp_2m",
        steps=30,
        cfg=8.5,
        width=1024,
        height=768,
        batch_size=2,
    )

    injected_workflow: dict[str, Any] = WorkflowParameterInjector().inject(workflow, parameters, {})

    assert injected_workflow["1"]["inputs"]["text"] == "cinematic city"
    assert injected_workflow["2"]["inputs"]["text"] == "low quality"
    assert injected_workflow["3"]["inputs"]["seed"] == 123
    assert injected_workflow["3"]["inputs"]["sampler_name"] == "dpmpp_2m"
    assert injected_workflow["3"]["inputs"]["steps"] == 30
    assert injected_workflow["3"]["inputs"]["cfg"] == 8.5
    assert injected_workflow["4"]["inputs"]["width"] == 1024
    assert injected_workflow["4"]["inputs"]["height"] == 768
    assert injected_workflow["4"]["inputs"]["batch_size"] == 2


def test_injector_applies_explicit_parameter_map() -> None:
    workflow: dict[str, Any] = {
        "10": {
            "class_type": "CustomPromptNode",
            "inputs": {"value": ""},
        },
    }
    parameter_map: dict[str, Any] = {
        "prompt": {"node_id": "10", "input": "value"},
    }
    parameters: WorkflowRuntimeParameters = WorkflowRuntimeParameters(prompt="mapped prompt")

    injected_workflow: dict[str, Any] = WorkflowParameterInjector().inject(
        workflow,
        parameters,
        parameter_map,
    )

    assert injected_workflow["10"]["inputs"]["value"] == "mapped prompt"


def test_template_loader_rejects_path_traversal() -> None:
    loader: WorkflowTemplateLoader = WorkflowTemplateLoader(Settings())

    with pytest.raises(WorkflowTemplateError):
        loader.load(mode=GenerationMode.TEXT_TO_IMAGE, workflow_name="../secret")
