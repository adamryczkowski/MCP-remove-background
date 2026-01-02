"""Custom exceptions for MCP Remove Background Server."""


class RemoveBackgroundError(Exception):
    """Base exception for MCP Remove Background errors."""

    pass


class ConfigurationError(RemoveBackgroundError):
    """Configuration-related errors."""

    pass


class InvalidRequestError(RemoveBackgroundError):
    """Invalid request parameters."""

    pass


class GenerationError(RemoveBackgroundError):
    """Background removal processing failures."""

    pass


class FileNotFoundError(RemoveBackgroundError):
    """Input file not found."""

    pass


class UnsupportedFormatError(RemoveBackgroundError):
    """Unsupported image format."""

    pass


class ModelNotFoundError(InvalidRequestError):
    """Requested model is not available."""

    pass
