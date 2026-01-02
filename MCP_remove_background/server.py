"""FastMCP server definition for Background Removal MCP.

This module defines the MCP server with tools for background removal.
"""

from fastmcp import FastMCP

from MCP_remove_background.constants import DEFAULT_MODEL, SUPPORTED_MODELS
from MCP_remove_background.tools.remove_background import (
    list_background_models as _list_background_models,
    remove_background as _remove_background,
)

# Create the MCP server instance
mcp = FastMCP("Background Removal MCP Server")


# ============================================================================
# TOOLS
# ============================================================================


@mcp.tool()
async def remove_background(
    image_path: str,
    output_path: str | None = None,
    model: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    try_floodfill_first: bool = True,
) -> dict:
    """Remove background from an image, producing PNG with transparency.

    Removes the background from an image using AI-powered segmentation.
    The image is specified by file path.

    Args:
        image_path: Path to the input image file.
        output_path: Path for the output image. If not provided, appends '_nobg' to input filename.
        model: Model for background removal. Options: {models}.
        alpha_matting: Enable alpha matting for smoother edges (slower but better quality).
        try_floodfill_first: Try fast flood-fill algorithm before ML-based approach.

    Returns:
        Dictionary with success status, file path, and metadata.
    """.format(models=", ".join(SUPPORTED_MODELS))
    result = await _remove_background(
        image_path=image_path,
        output_path=output_path,
        model=model,
        alpha_matting=alpha_matting,
        try_floodfill_first=try_floodfill_first,
    )
    return result.model_dump()


@mcp.tool()
def list_background_models() -> dict:
    """List all available background removal models.

    Returns a list of models that can be used for background removal,
    including their descriptions and recommended use cases.

    Returns:
        Dictionary with models list and default model information.
    """
    result = _list_background_models()
    return result.model_dump()


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    mcp.run()
