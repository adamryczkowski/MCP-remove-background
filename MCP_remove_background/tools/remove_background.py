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
)
from MCP_remove_background.exceptions import GenerationError, InvalidRequestError
from MCP_remove_background.services.background_remover import (
    get_available_models,
    remove_background_from_file,
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

        return RemoveBackgroundOutput(
            success=True,
            input_path=image_path,
            output_path=result_path,
            file_size_bytes=file_size,
            method_used=method_used,
            model_used=model,
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
