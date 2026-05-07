# Workflow Templates

ComfyUI workflow templates are loaded from this directory.

Supported default filenames:

* `t2i.json`
* `i2i.json`
* `t2v.json`
* `i2v.json`

Templates may be plain ComfyUI API JSON exports, or wrapped with explicit runtime injection metadata:

```json
{
    "workflow": {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": ""
            }
        }
    },
    "parameter_map": {
        "prompt": {
            "node_id": "1",
            "input": "text"
        }
    }
}
```

When no `parameter_map` is present, the backend injects common ComfyUI node inputs by class name for prompts, negative prompts, seeds, samplers, dimensions, LoRA nodes, image inputs, and video inputs.
