"""Background removal service using rembg library and flood-fill algorithm.

This module provides background removal functionality for images using:
1. Flood-fill algorithm for images with uniform background colors
2. Deep learning models via the rembg library for complex backgrounds

The flood-fill approach is attempted first when border pixels have similar
colors (within a perceptual threshold), as it's faster and produces clean
results for AI-generated images with solid backgrounds.

The service includes automatic model unloading after a configurable idle
period to conserve RAM when not in use.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from MCP_remove_background.constants import (
    DEFAULT_COLOR_THRESHOLD,
    DEFAULT_MODEL,
    DEFAULT_MODEL_IDLE_TIMEOUT,
    MIN_UNIFORM_BORDER_PERCENTAGE,
    MODEL_METADATA,
    OUTPUT_SUFFIX,
    SUPPORTED_MODELS,
)
from MCP_remove_background.exceptions import (
    FileNotFoundError as FileNotFoundErr,
    GenerationError,
    InvalidRequestError,
)

logger = logging.getLogger(__name__)

# Global session cache for model reuse
# Using Any type since BaseSession is not exported from rembg
_session_cache: dict[str, Any] = {}

# Track last usage time for auto-unload
_last_usage_time: float = 0.0

# Timer for auto-unload
_unload_timer: threading.Timer | None = None

# Lock for thread-safe cache operations
_cache_lock = threading.Lock()

# Current idle timeout setting (can be modified at runtime)
_idle_timeout: float = float(DEFAULT_MODEL_IDLE_TIMEOUT)


def get_border_pixels(image: Image.Image) -> list[tuple[int, int]]:
    """Get all pixel coordinates along the image border.

    Args:
        image: PIL Image to get border pixels from.

    Returns:
        List of (x, y) coordinates for all border pixels.
    """
    width, height = image.size
    border_pixels = []

    # Top and bottom rows
    for x in range(width):
        border_pixels.append((x, 0))
        border_pixels.append((x, height - 1))

    # Left and right columns (excluding corners already added)
    for y in range(1, height - 1):
        border_pixels.append((0, y))
        border_pixels.append((width - 1, y))

    return border_pixels


def color_distance(color1: tuple, color2: tuple) -> float:
    """Calculate perceptual color distance between two RGB/RGBA colors.

    Uses a weighted Euclidean distance that accounts for human perception
    (green is more perceptible than red, which is more than blue).

    Args:
        color1: First color as RGB or RGBA tuple.
        color2: Second color as RGB or RGBA tuple.

    Returns:
        Perceptual color distance (0 = identical, higher = more different).
    """
    # Use only RGB components (ignore alpha if present)
    # Convert to int to avoid overflow with uint8
    r1, g1, b1 = int(color1[0]), int(color1[1]), int(color1[2])
    r2, g2, b2 = int(color2[0]), int(color2[1]), int(color2[2])

    # Weighted distance based on human perception
    # Red: 0.3, Green: 0.59, Blue: 0.11 (standard luminance weights)
    rmean = (r1 + r2) / 2
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2

    # Redmean color difference formula (more accurate than simple Euclidean)
    return float(
        np.sqrt(
            (2 + rmean / 256) * dr * dr
            + 4 * dg * dg
            + (2 + (255 - rmean) / 256) * db * db
        )
    )


def check_border_uniformity(
    image: Image.Image,
    threshold: float = DEFAULT_COLOR_THRESHOLD,
) -> tuple[bool, tuple[int, int, int] | None]:
    """Check if all border pixels have similar colors.

    Args:
        image: PIL Image to check.
        threshold: Maximum color distance for pixels to be considered similar.

    Returns:
        Tuple of (is_uniform, median_color) where is_uniform is True if
        at least MIN_UNIFORM_BORDER_PERCENTAGE of border pixels are within
        threshold of the median border color.
    """
    # Convert to RGB if necessary
    if image.mode != "RGB":
        rgb_image = image.convert("RGB")
    else:
        rgb_image = image

    border_pixels = get_border_pixels(rgb_image)
    border_colors: list[tuple[int, ...]] = [
        rgb_image.getpixel(pos)
        for pos in border_pixels  # type: ignore[misc]
    ]

    if not border_colors:
        return False, None

    # Calculate median color (more robust than mean for outliers)
    colors_array = np.array(border_colors)
    median_values = np.median(colors_array, axis=0)
    median_color: tuple[int, int, int] = (
        int(median_values[0]),
        int(median_values[1]),
        int(median_values[2]),
    )

    # Count how many border pixels are within threshold of median
    uniform_count = sum(
        1 for color in border_colors if color_distance(color, median_color) <= threshold
    )

    uniformity_ratio = uniform_count / len(border_colors)
    is_uniform = uniformity_ratio >= MIN_UNIFORM_BORDER_PERCENTAGE

    logger.debug(
        f"Border uniformity check: {uniformity_ratio:.1%} uniform "
        f"(threshold: {MIN_UNIFORM_BORDER_PERCENTAGE:.0%}), "
        f"median color: {median_color}"
    )

    return is_uniform, median_color


def flood_fill_transparency(
    image: Image.Image,
    background_color: tuple[int, int, int],
    threshold: float = DEFAULT_COLOR_THRESHOLD,
) -> Image.Image:
    """Remove background using flood-fill from all border pixels.

    This algorithm starts from all border pixels and flood-fills inward,
    making all pixels within the color threshold transparent.

    Args:
        image: PIL Image to process.
        background_color: The background color to make transparent.
        threshold: Maximum color distance for pixels to be considered background.

    Returns:
        RGBA image with background made transparent.
    """
    # Convert to RGB for processing
    if image.mode != "RGB":
        rgb_image = image.convert("RGB")
    else:
        rgb_image = image.copy()

    width, height = rgb_image.size
    pixels = np.array(rgb_image)

    # Create alpha channel (255 = opaque, 0 = transparent)
    alpha = np.full((height, width), 255, dtype=np.uint8)

    # Track visited pixels
    visited = np.zeros((height, width), dtype=bool)

    # Get all border pixels as starting points
    border_pixels = get_border_pixels(rgb_image)

    # Use BFS flood-fill from all border pixels
    queue = deque()

    # Initialize queue with border pixels that match background color
    for x, y in border_pixels:
        if not visited[y, x]:
            pixel_color = tuple(pixels[y, x])
            if color_distance(pixel_color, background_color) <= threshold:
                queue.append((x, y))
                visited[y, x] = True
                alpha[y, x] = 0

    # 4-connected neighbors (up, down, left, right)
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    # Flood-fill
    while queue:
        x, y = queue.popleft()

        for dx, dy in directions:
            nx, ny = x + dx, y + dy

            # Check bounds
            if 0 <= nx < width and 0 <= ny < height and not visited[ny, nx]:
                visited[ny, nx] = True
                pixel_color = tuple(pixels[ny, nx])

                if color_distance(pixel_color, background_color) <= threshold:
                    alpha[ny, nx] = 0
                    queue.append((nx, ny))

    # Create RGBA image
    rgba_pixels = np.dstack((pixels, alpha))
    result = Image.fromarray(rgba_pixels)

    # Count transparent pixels for logging
    transparent_count = np.sum(alpha == 0)
    total_pixels = width * height
    logger.info(
        f"Flood-fill complete: {transparent_count}/{total_pixels} pixels "
        f"({transparent_count / total_pixels:.1%}) made transparent"
    )

    return result


def remove_background_floodfill(
    image: Image.Image,
    threshold: float = DEFAULT_COLOR_THRESHOLD,
) -> Image.Image | None:
    """Attempt to remove background using flood-fill algorithm.

    This function first checks if the image has a uniform border color.
    If so, it uses flood-fill to make the background transparent.
    If not, it returns None to indicate ML-based approach should be used.

    Args:
        image: PIL Image to process.
        threshold: Color distance threshold for background detection.

    Returns:
        RGBA image with transparent background, or None if flood-fill
        is not suitable for this image.
    """
    is_uniform, background_color = check_border_uniformity(image, threshold)

    if not is_uniform or background_color is None:
        logger.info(
            "Border is not uniform enough for flood-fill, "
            "falling back to ML-based approach"
        )
        return None

    logger.info(f"Using flood-fill algorithm with background color {background_color}")
    return flood_fill_transparency(image, background_color, threshold)


def _cancel_unload_timer() -> None:
    """Cancel any pending auto-unload timer."""
    global _unload_timer
    if _unload_timer is not None:
        _unload_timer.cancel()
        _unload_timer = None


def _schedule_auto_unload() -> None:
    """Schedule automatic model unloading after idle timeout.

    This function cancels any existing timer and schedules a new one
    if the idle timeout is greater than 0.
    """
    global _unload_timer, _last_usage_time

    _cancel_unload_timer()

    if _idle_timeout <= 0:
        return  # Auto-unload disabled

    def _auto_unload() -> None:
        """Callback to unload models after idle timeout."""
        global _unload_timer
        with _cache_lock:
            if _session_cache:
                elapsed = time.time() - _last_usage_time
                if elapsed >= _idle_timeout:
                    logger.info(
                        f"Auto-unloading models after {elapsed:.1f}s idle "
                        f"(timeout: {_idle_timeout}s)"
                    )
                    _session_cache.clear()
                    _unload_timer = None
                else:
                    # Reschedule if there was recent activity
                    remaining = _idle_timeout - elapsed
                    _unload_timer = threading.Timer(remaining, _auto_unload)
                    _unload_timer.daemon = True
                    _unload_timer.start()

    _unload_timer = threading.Timer(_idle_timeout, _auto_unload)
    _unload_timer.daemon = True
    _unload_timer.start()
    logger.debug(f"Scheduled auto-unload in {_idle_timeout}s")


def _update_last_usage() -> None:
    """Update the last usage timestamp and reschedule auto-unload."""
    global _last_usage_time
    _last_usage_time = time.time()
    _schedule_auto_unload()


def set_idle_timeout(timeout_seconds: float) -> None:
    """Set the idle timeout for automatic model unloading.

    Args:
        timeout_seconds: Timeout in seconds. Set to 0 to disable auto-unload.
    """
    global _idle_timeout
    _idle_timeout = max(0.0, timeout_seconds)
    logger.info(f"Model idle timeout set to {_idle_timeout}s")

    if _session_cache:
        # Reschedule with new timeout
        _schedule_auto_unload()


def get_idle_timeout() -> float:
    """Get the current idle timeout setting.

    Returns:
        Current idle timeout in seconds.
    """
    return _idle_timeout


def get_session(model: str) -> Any:
    """Get or create a rembg session for the specified model.

    Sessions are cached to avoid reloading models on each request.
    Accessing a session updates the last usage time for auto-unload.

    Args:
        model: The model name to use for background removal.

    Returns:
        A rembg session configured with the specified model.

    Raises:
        InvalidRequestError: If the model is not supported.
        GenerationError: If the session cannot be created.
    """
    if model not in SUPPORTED_MODELS:
        raise InvalidRequestError(
            f"Unsupported background removal model: {model}. "
            f"Supported models: {', '.join(SUPPORTED_MODELS)}"
        )

    with _cache_lock:
        if model not in _session_cache:
            try:
                # Import here to avoid loading rembg at module import time
                from rembg import new_session

                logger.info(f"Creating new rembg session with model: {model}")
                _session_cache[model] = new_session(model)
                logger.info(f"Successfully created session for model: {model}")
            except Exception as e:
                logger.error(f"Failed to create rembg session: {e}")
                raise GenerationError(
                    f"Failed to initialize background removal model '{model}': {e}"
                ) from e

        # Update usage time and reschedule auto-unload
        _update_last_usage()

        return _session_cache[model]


def remove_background_from_bytes(
    image_bytes: bytes,
    model: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    try_floodfill_first: bool = True,
    floodfill_threshold: float = DEFAULT_COLOR_THRESHOLD,
) -> tuple[bytes, str]:
    """Remove background from image bytes.

    This function first attempts to use a fast flood-fill algorithm if the
    image has a uniform border color. If flood-fill is not suitable (border
    colors vary too much), it falls back to the ML-based approach.

    Args:
        image_bytes: The input image as bytes.
        model: The model to use for ML-based background removal.
        alpha_matting: Whether to use alpha matting for smoother edges.
        alpha_matting_foreground_threshold: Foreground threshold for alpha matting.
        alpha_matting_background_threshold: Background threshold for alpha matting.
        try_floodfill_first: Whether to attempt flood-fill before ML approach.
        floodfill_threshold: Color distance threshold for flood-fill algorithm.

    Returns:
        Tuple of (PNG image bytes with transparent background, method used).
        Method is either "floodfill" or the model name.

    Raises:
        InvalidRequestError: If the model is not supported.
        GenerationError: If background removal fails.
    """
    try:
        # Open image
        input_image = Image.open(io.BytesIO(image_bytes))
        logger.debug(f"Processing image: {input_image.size}, mode={input_image.mode}")

        output_image = None
        method_used = model

        # Try flood-fill first if enabled
        if try_floodfill_first:
            output_image = remove_background_floodfill(
                input_image, threshold=floodfill_threshold
            )
            if output_image is not None:
                method_used = "floodfill"

        # Fall back to ML-based approach if flood-fill didn't work
        if output_image is None:
            # Import here to avoid loading rembg at module import time
            from rembg import remove

            # Get or create session
            session = get_session(model)

            # Remove background using ML
            ml_result = remove(
                input_image,
                session=session,
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                alpha_matting_background_threshold=alpha_matting_background_threshold,
            )
            # rembg.remove returns PIL.Image.Image
            if isinstance(ml_result, Image.Image):
                output_image = ml_result
            else:
                # Handle bytes or ndarray return types
                output_image = Image.open(io.BytesIO(ml_result))  # type: ignore[arg-type]

        # Convert to PNG bytes
        output_buffer = io.BytesIO()
        output_image.save(output_buffer, format="PNG")
        result_bytes = output_buffer.getvalue()

        logger.info(
            f"Background removed successfully using {method_used}. "
            f"Input: {len(image_bytes)} bytes, Output: {len(result_bytes)} bytes"
        )

        return result_bytes, method_used

    except InvalidRequestError:
        raise
    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        raise GenerationError(f"Failed to remove background: {e}") from e


def remove_background_from_file(
    input_path: str,
    output_path: str | None = None,
    model: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    try_floodfill_first: bool = True,
) -> tuple[str, str]:
    """Remove background from an image file.

    Args:
        input_path: Path to the input image file.
        output_path: Path for the output image. If None, appends '_nobg' to input name.
        model: The model to use for background removal.
        alpha_matting: Whether to use alpha matting for smoother edges.
        try_floodfill_first: Whether to attempt flood-fill before ML approach.

    Returns:
        Tuple of (path to the output image file, method used).

    Raises:
        FileNotFoundError: If the input file does not exist.
        InvalidRequestError: If the model is not supported.
        GenerationError: If background removal fails.
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundErr(f"Input file not found: {input_path}")

    # Generate output path if not provided
    if output_path is None:
        output_path = str(input_file.parent / f"{input_file.stem}{OUTPUT_SUFFIX}.png")

    try:
        # Read input file
        image_bytes = input_file.read_bytes()

        # Remove background
        result_bytes, method_used = remove_background_from_bytes(
            image_bytes,
            model=model,
            alpha_matting=alpha_matting,
            try_floodfill_first=try_floodfill_first,
        )

        # Write output file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(result_bytes)

        logger.info(
            f"Saved background-removed image to: {output_path} (method: {method_used})"
        )
        return str(output_file.absolute()), method_used

    except (InvalidRequestError, FileNotFoundErr):
        raise
    except Exception as e:
        logger.error(f"Failed to process file: {e}")
        raise GenerationError(f"Failed to process file '{input_path}': {e}") from e


def get_available_models() -> list[dict[str, str]]:
    """Get list of available background removal models with descriptions.

    Returns:
        List of dictionaries with model info (id, name, description, size).
    """
    return [MODEL_METADATA[model_id] for model_id in SUPPORTED_MODELS]


def clear_session_cache() -> None:
    """Clear the session cache to free memory.

    This should be called when shutting down the server or when
    memory usage needs to be reduced.
    """
    with _cache_lock:
        _cancel_unload_timer()
        _session_cache.clear()
        logger.info("Cleared background removal session cache")


def get_loaded_models() -> list[str]:
    """Get list of currently loaded model names.

    Returns:
        List of model IDs that are currently loaded in memory.
    """
    with _cache_lock:
        return list(_session_cache.keys())


def unload_models() -> dict[str, Any]:
    """Unload all cached ML models to free memory.

    This function immediately unloads all cached background removal models
    and cancels any pending auto-unload timer.

    Returns:
        Dictionary with unload status including:
        - success: Whether unload was successful
        - models_unloaded: List of model IDs that were unloaded
        - models_count: Number of models that were unloaded
        - message: Human-readable status message
    """
    with _cache_lock:
        models_unloaded = list(_session_cache.keys())
        models_count = len(models_unloaded)

        _cancel_unload_timer()
        _session_cache.clear()

        if models_count > 0:
            message = f"Successfully unloaded {models_count} model(s): {', '.join(models_unloaded)}"
            logger.info(message)
        else:
            message = "No models were loaded"
            logger.info(message)

        return {
            "success": True,
            "models_unloaded": models_unloaded,
            "models_count": models_count,
            "message": message,
        }


def get_cache_status() -> dict[str, Any]:
    """Get current status of the model cache.

    Returns:
        Dictionary with cache status including:
        - loaded_models: List of currently loaded model IDs
        - models_count: Number of loaded models
        - idle_timeout: Current idle timeout setting in seconds
        - auto_unload_enabled: Whether auto-unload is enabled
        - last_usage_time: Timestamp of last model usage (0 if never used)
        - time_until_unload: Seconds until auto-unload (None if disabled or no models)
    """
    with _cache_lock:
        loaded_models = list(_session_cache.keys())
        models_count = len(loaded_models)

        time_until_unload = None
        if _idle_timeout > 0 and models_count > 0 and _last_usage_time > 0:
            elapsed = time.time() - _last_usage_time
            time_until_unload = max(0.0, _idle_timeout - elapsed)

        return {
            "loaded_models": loaded_models,
            "models_count": models_count,
            "idle_timeout": _idle_timeout,
            "auto_unload_enabled": _idle_timeout > 0,
            "last_usage_time": _last_usage_time,
            "time_until_unload": time_until_unload,
        }
