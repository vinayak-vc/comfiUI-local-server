"""Storage layer exceptions."""


class StorageError(Exception):
    """Base exception for storage failures."""


class StorageValidationError(StorageError):
    """Raised when an uploaded asset fails validation."""


class AssetNotFoundError(StorageError):
    """Raised when an asset metadata record or file is missing."""
