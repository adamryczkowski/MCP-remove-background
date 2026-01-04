"""Background removal tools for MCP server.

This module provides MCP tools for removing backgrounds from images.
All image data is passed via file paths only - no base64 encoding.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from MCP_remove_background.constants import (
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
    UNLOAD_HINT,
)
from MCP_remove_background.exceptions import GenerationError, InvalidRequestError
from MCP_remove_background.services.background_remover import (
    get_available_models,
    get_cache_status,
    remove_background_from_file,
    unload_models as service_unload_models,
)


class RemoveBackgroundInput(BaseModel):
    """Input schema for remove_background tool."""

    image_path: str = Field(
        description="Path to the input image file.",
    )
    output_path: str | None = Field(
        default=None,
        description="Path for the output image. If not provided, appends '_nobg' to input filename.",
    )
    model: str = Field(
        default=DEFAULT_MODEL,
        description=f"Model to use for background removal. Options: {', '.join(SUPPORTED_MODELS)}",
    )
    alpha_matting: bool = Field(
        default=False,
        description="Enable alpha matting for smoother edges (slower but better quality).",
    )
    try_floodfill_first: bool = Field(
        default=True,
        description="Try fast flood-fill algorithm before ML-based approach.",
    )


class RemoveBackgroundOutput(BaseModel):
    """Output schema for remove_background tool."""

    success: bool = Field(description="Whether the background removal was successful")
    input_path: str = Field(description="Path to the input image file")
    output_path: str | None = Field(
        default=None, description="Path to the output image file"
    )
    file_size_bytes: int | None = Field(
        default=None, description="Size of the output image in bytes"
    )
    method_used: str = Field(
        default="",
        description="Method used for background removal: 'floodfill' or model name",
    )
    model_used: str = Field(
        description="Model that was configured for background removal"
    )
    error: str | None = Field(
        default=None, description="Error message if background removal failed"
    )
    hint: str | None = Field(
        default=None,
        description="Helpful tip about memory management after using ML models",
    )


class UnloadModelsOutput(BaseModel):
    """Output schema for unload_models tool."""

    success: bool = Field(description="Whether unload was successful")
    models_unloaded: list[str] = Field(
        description="List of model IDs that were unloaded"
    )
    models_count: int = Field(description="Number of models that were unloaded")
    message: str = Field(description="Human-readable status message")


class CacheStatusOutput(BaseModel):
    """Output schema for get_cache_status tool."""

    loaded_models: list[str] = Field(description="List of currently loaded model IDs")
    models_count: int = Field(description="Number of loaded models")
    idle_timeout: float = Field(description="Current idle timeout setting in seconds")
    auto_unload_enabled: bool = Field(description="Whether auto-unload is enabled")
    last_usage_time: float = Field(
        description="Timestamp of last model usage (0 if never used)"
    )
    time_until_unload: float | None = Field(
        default=None,
        description="Seconds until auto-unload (None if disabled or no models)",
    )


class ListModelsOutput(BaseModel):
    """Output schema for list_background_models tool."""

    models: list[dict[str, str]] = Field(
        description="List of available background removal models"
    )
    total_count: int = Field(description="Total number of available models")
    default_model: str = Field(description="The default model used if none specified")
    usage_hint: str = Field(description="Hint on how to use the models")


async def remove_background(
    image_path: str,
    output_path: str | None = None,
    model: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    try_floodfill_first: bool = True,
) -> RemoveBackgroundOutput:
    """Remove background from an image.

    Removes the background from an image and returns a PNG with transparent
    background. The image is specified by file path.

    Args:
        image_path: Path to the input image file.
        output_path: Path for the output image. If not provided,
            appends '_nobg' to the input filename.
        model: Model to use for background removal.
        alpha_matting: Enable alpha matting for smoother edges.
        try_floodfill_first: Try fast flood-fill before ML approach.

    Returns:
        RemoveBackgroundOutput with the result.
    """
    # Validate model
    if model not in SUPPORTED_MODELS:
        return RemoveBackgroundOutput(
            success=False,
            input_path=image_path,
            model_used=model,
            error=f"Invalid model: {model}. Available models: {', '.join(SUPPORTED_MODELS)}",
        )

    # Check if input file exists
    input_file = Path(image_path)
    if not input_file.exists():
        return RemoveBackgroundOutput(
            success=False,
            input_path=image_path,
            model_used=model,
            error=f"Input file not found: {image_path}",
        )

    try:
        # Process file input
        result_path, method_used = remove_background_from_file(
            input_path=image_path,
            output_path=output_path,
            model=model,
            alpha_matting=alpha_matting,
            try_floodfill_first=try_floodfill_first,
        )

        # Get file size
        file_size = Path(result_path).stat().st_size

        # Add hint when ML model was used (not floodfill)
        hint = UNLOAD_HINT if method_used != "floodfill" else None

        return RemoveBackgroundOutput(
            success=True,
            input_path=image_path,
            output_path=result_path,
            file_size_bytes=file_size,
            method_used=method_used,
            model_used=model,
            hint=hint,
        )

    except InvalidRequestError as e:
        return RemoveBackgroundOutput(
            success=False,
            input_path=image_path,
            model_used=model,
            error=f"Invalid request: {e}",
        )
    except GenerationError as e:
        return RemoveBackgroundOutput(
            success=False,
            input_path=image_path,
            model_used=model,
            error=f"Background removal failed: {e}",
        )
    except Exception as e:
        return RemoveBackgroundOutput(
            success=False,
            input_path=image_path,
            model_used=model,
            error=f"Unexpected error: {e}",
        )


def list_background_models() -> ListModelsOutput:
    """List available background removal models.

    Returns:
        ListModelsOutput with model information.
    """
    models = get_available_models()
    return ListModelsOutput(
        models=models,
        total_count=len(models),
        default_model=DEFAULT_MODEL,
        usage_hint="Use the 'model' parameter in remove_background to specify which model to use.",
    )


def unload_models() -> UnloadModelsOutput:
    """Unload all cached ML models to free memory.

    Call this tool when you're done processing images to free up RAM.
    ML models can consume 100MB-400MB each.

    Returns:
        UnloadModelsOutput with unload status.
    """
    result = service_unload_models()
    return UnloadModelsOutput(
        success=result["success"],
        models_unloaded=result["models_unloaded"],
        models_count=result["models_count"],
        message=result["message"],
    )


def get_model_cache_status() -> CacheStatusOutput:
    """Get current status of the model cache.

    Returns information about loaded models, auto-unload settings,
    and time until automatic unload.

    Returns:
        CacheStatusOutput with cache status.
    """
    status = get_cache_status()
    return CacheStatusOutput(
        loaded_models=status["loaded_models"],
        models_count=status["models_count"],
        idle_timeout=status["idle_timeout"],
        auto_unload_enabled=status["auto_unload_enabled"],
        last_usage_time=status["last_usage_time"],
        time_until_unload=status["time_until_unload"],
    )
