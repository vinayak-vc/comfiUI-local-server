"""Runtime parameter injection for ComfyUI workflow templates."""

from typing import Any

from app.comfy.exceptions import WorkflowTemplateError
from app.schemas.comfy import LoraInjection, WorkflowRuntimeParameters


class WorkflowParameterInjector:
    """Injects runtime values into a cloned ComfyUI workflow graph."""

    def inject(
        self,
        workflow: dict[str, Any],
        parameters: WorkflowRuntimeParameters,
        parameter_map: dict[str, Any],
    ) -> dict[str, Any]:
        if parameter_map:
            self._inject_from_parameter_map(workflow, parameters, parameter_map)
        else:
            self._inject_by_node_conventions(workflow, parameters)

        self._inject_extra_parameters(workflow, parameters.extra_parameters)
        return workflow

    def _inject_from_parameter_map(
        self,
        workflow: dict[str, Any],
        parameters: WorkflowRuntimeParameters,
        parameter_map: dict[str, Any],
    ) -> None:
        parameter_values: dict[str, Any] = parameters.model_dump()
        for parameter_name, raw_targets in parameter_map.items():
            if parameter_name not in parameter_values:
                continue

            value: Any = parameter_values[parameter_name]
            if value is None:
                continue

            targets: list[Any] = raw_targets if isinstance(raw_targets, list) else [raw_targets]
            for target in targets:
                if not isinstance(target, dict):
                    raise WorkflowTemplateError("Parameter map targets must be objects.")
                self._set_mapped_value(workflow, target, value)

    def _set_mapped_value(self, workflow: dict[str, Any], target: dict[str, Any], value: Any) -> None:
        node_id: Any = target.get("node_id")
        input_name: Any = target.get("input")
        if not isinstance(node_id, str) or not isinstance(input_name, str):
            raise WorkflowTemplateError("Parameter map target requires node_id and input.")

        node: dict[str, Any] = self._get_node(workflow, node_id)
        inputs: dict[str, Any] = self._get_inputs(node, node_id)
        inputs[input_name] = value

    def _inject_by_node_conventions(
        self,
        workflow: dict[str, Any],
        parameters: WorkflowRuntimeParameters,
    ) -> None:
        text_nodes: list[dict[str, Any]] = []
        lora_nodes: list[dict[str, Any]] = []

        for node_id, node in workflow.items():
            if not isinstance(node_id, str) or not isinstance(node, dict):
                continue

            class_type: str = self._get_class_type(node)
            inputs: dict[str, Any] = self._get_inputs(node, node_id)

            if "CLIPTextEncode" in class_type:
                text_nodes.append(inputs)
            elif class_type == "KSampler":
                self._set_if_present(inputs, "seed", parameters.seed)
                self._set_if_present(inputs, "sampler_name", parameters.sampler)
                self._set_if_present(inputs, "scheduler", parameters.scheduler)
                self._set_if_present(inputs, "steps", parameters.steps)
                self._set_if_present(inputs, "cfg", parameters.cfg)
                self._set_if_present(inputs, "denoise", parameters.denoise)
            elif class_type in {"EmptyLatentImage", "EmptySD3LatentImage"}:
                self._set_if_present(inputs, "width", parameters.width)
                self._set_if_present(inputs, "height", parameters.height)
                self._set_if_present(inputs, "batch_size", parameters.batch_size)
            elif class_type in {"CheckpointLoaderSimple", "UNETLoader"}:
                self._set_if_present(inputs, "ckpt_name", parameters.model)
                self._set_if_present(inputs, "unet_name", parameters.model)
            elif class_type == "LoraLoader":
                lora_nodes.append(inputs)
            elif class_type in {"LoadImage", "LoadImageMask"}:
                self._set_if_present(inputs, "image", parameters.input_image)
            elif class_type in {"VHS_LoadVideo", "LoadVideo", "VideoLoader"}:
                self._set_if_present(inputs, "video", parameters.input_video)
                self._set_if_present(inputs, "video_path", parameters.input_video)

        if text_nodes:
            text_nodes[0]["text"] = parameters.prompt
        if len(text_nodes) > 1 and parameters.negative_prompt is not None:
            text_nodes[1]["text"] = parameters.negative_prompt

        self._inject_loras(lora_nodes, parameters.loras)

    def _inject_loras(self, lora_nodes: list[dict[str, Any]], loras: list[LoraInjection]) -> None:
        for index, lora in enumerate(loras):
            if index >= len(lora_nodes):
                raise WorkflowTemplateError("Workflow does not contain enough LoraLoader nodes.")

            inputs: dict[str, Any] = lora_nodes[index]
            inputs["lora_name"] = lora.name
            inputs["strength_model"] = lora.strength_model
            inputs["strength_clip"] = lora.strength_clip

    def _inject_extra_parameters(self, workflow: dict[str, Any], extra_parameters: dict[str, Any]) -> None:
        for raw_target, value in extra_parameters.items():
            if value is None:
                continue

            target_parts: list[str] = raw_target.split(".")
            if len(target_parts) != 2:
                raise WorkflowTemplateError("Extra parameter keys must use node_id.input format.")

            node_id: str = target_parts[0]
            input_name: str = target_parts[1]
            node: dict[str, Any] = self._get_node(workflow, node_id)
            inputs: dict[str, Any] = self._get_inputs(node, node_id)
            inputs[input_name] = value

    def _get_node(self, workflow: dict[str, Any], node_id: str) -> dict[str, Any]:
        node: Any = workflow.get(node_id)
        if not isinstance(node, dict):
            raise WorkflowTemplateError(f"Workflow node does not exist: {node_id}")
        return node

    def _get_inputs(self, node: dict[str, Any], node_id: str) -> dict[str, Any]:
        inputs: Any = node.get("inputs")
        if not isinstance(inputs, dict):
            raise WorkflowTemplateError(f"Workflow node has no inputs object: {node_id}")
        return inputs

    def _get_class_type(self, node: dict[str, Any]) -> str:
        class_type: Any = node.get("class_type", "")
        return class_type if isinstance(class_type, str) else ""

    def _set_if_present(self, inputs: dict[str, Any], input_name: str, value: Any) -> None:
        if value is not None and input_name in inputs:
            inputs[input_name] = value
