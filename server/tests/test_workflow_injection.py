"""Workflow parameter injection tests."""

from typing import Any

import pytest

from app.comfy.exceptions import WorkflowTemplateError
from app.core.config import Settings
from app.schemas.comfy import GenerationMode, WorkflowExecutionRequest, WorkflowRuntimeParameters
from app.workflows.builder import WorkflowBuilder
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


def test_injector_applies_flux_sd3_latent_dimensions() -> None:
    workflow: dict[str, Any] = {
        "27": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1,
            },
        },
    }
    parameters: WorkflowRuntimeParameters = WorkflowRuntimeParameters(
        width=768,
        height=1344,
        batch_size=2,
    )

    injected_workflow: dict[str, Any] = WorkflowParameterInjector().inject(workflow, parameters, {})

    assert injected_workflow["27"]["inputs"]["width"] == 768
    assert injected_workflow["27"]["inputs"]["height"] == 1344
    assert injected_workflow["27"]["inputs"]["batch_size"] == 2


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


def test_injector_rejects_loras_when_workflow_has_no_lora_nodes() -> None:
    workflow: dict[str, Any] = {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ""},
        },
    }
    parameters: WorkflowRuntimeParameters = WorkflowRuntimeParameters(
        loras=[
            {
                "name": "example.safetensors",
                "strength_model": 1.0,
                "strength_clip": 1.0,
            }
        ],
    )

    with pytest.raises(WorkflowTemplateError, match="Workflow does not contain enough LoraLoader nodes"):
        WorkflowParameterInjector().inject(workflow, parameters, {})


def test_template_loader_rejects_path_traversal() -> None:
    loader: WorkflowTemplateLoader = WorkflowTemplateLoader(Settings())

    with pytest.raises(WorkflowTemplateError):
        loader.load(mode=GenerationMode.TEXT_TO_IMAGE, workflow_name="../secret")


def test_default_execution_request_builds_flux_schnell_workflow() -> None:
    request: WorkflowExecutionRequest = WorkflowExecutionRequest()
    workflow: dict[str, Any] = WorkflowBuilder(Settings()).build(
        request.mode,
        request.parameters,
        request.workflow_name,
    )

    assert request.mode == GenerationMode.TEXT_TO_IMAGE
    assert request.workflow_name == "flux_schnell"
    assert workflow["6"]["inputs"]["text"] == request.parameters.prompt
    assert workflow["30"]["inputs"]["ckpt_name"] == "flux1-schnell-fp8.safetensors"
    assert workflow["31"]["inputs"]["steps"] == 4
    assert workflow["31"]["inputs"]["sampler_name"] == "euler"
    assert workflow["31"]["inputs"]["scheduler"] == "simple"
    assert workflow["27"]["inputs"]["width"] == 1024
