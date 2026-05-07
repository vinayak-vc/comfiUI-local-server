"""ComfyUI integration exceptions."""


class ComfyUIError(Exception):
    """Base exception for ComfyUI integration failures."""


class ComfyUIConnectionError(ComfyUIError):
    """Raised when ComfyUI cannot be reached."""


class ComfyUIResponseError(ComfyUIError):
    """Raised when ComfyUI returns malformed or failed responses."""


class WorkflowTemplateError(ComfyUIError):
    """Raised when a workflow template cannot be loaded or transformed."""


class WorkflowExecutionError(ComfyUIError):
    """Raised when workflow execution fails."""
