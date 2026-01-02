"""Mock for rembg library to avoid downloading models during testing.

This module provides mock implementations of rembg functions that can be used
in tests to avoid the overhead of loading actual ML models.
"""

from __future__ import annotations

from typing import Any

from PIL import Image


class MockSession:
    """Mock rembg session object."""

    def __init__(self, model_name: str) -> None:
        """Initialize mock session.

        Args:
            model_name: The model name this session was created for.
        """
        self.model_name = model_name

    def __repr__(self) -> str:
        """Return string representation."""
        return f"MockSession(model_name={self.model_name!r})"


def mock_new_session(model_name: str) -> MockSession:
    """Create a mock rembg session.

    Args:
        model_name: The model name to create a session for.

    Returns:
        A MockSession object.
    """
    return MockSession(model_name)


def mock_remove(
    image: Image.Image,
    session: MockSession | None = None,
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    **kwargs: Any,
) -> Image.Image:
    """Mock rembg.remove function.

    This function simulates background removal by converting the image to RGBA
    and making a simple transformation (making white pixels transparent).

    Args:
        image: Input PIL Image.
        session: Mock session object (unused in mock).
        alpha_matting: Whether to use alpha matting (unused in mock).
        alpha_matting_foreground_threshold: Foreground threshold (unused in mock).
        alpha_matting_background_threshold: Background threshold (unused in mock).
        **kwargs: Additional keyword arguments (unused).

    Returns:
        RGBA image with simulated transparent background.
    """
    # Convert to RGBA
    if image.mode != "RGBA":
        rgba_image = image.convert("RGBA")
    else:
        rgba_image = image.copy()

    # Simple mock: make white-ish pixels transparent
    # This simulates background removal without actual ML
    pixels = rgba_image.load()
    if pixels is None:
        return rgba_image

    width, height = rgba_image.size

    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            if isinstance(pixel, tuple) and len(pixel) >= 4:
                r, g, b, _a = pixel[0], pixel[1], pixel[2], pixel[3]
                # If pixel is white-ish (all channels > 240), make transparent
                if r > 240 and g > 240 and b > 240:
                    pixels[x, y] = (r, g, b, 0)

    return rgba_image


def apply_rembg_mocks(monkeypatch: Any) -> None:
    """Apply rembg mocks using pytest monkeypatch.

    This function patches the rembg module functions with mock implementations.

    Args:
        monkeypatch: pytest monkeypatch fixture.
    """
    import sys

    # Import rembg to ensure it's in sys.modules
    try:
        import rembg

        # Patch the functions on the actual module
        monkeypatch.setattr(rembg, "remove", mock_remove)
        monkeypatch.setattr(rembg, "new_session", mock_new_session)
    except ImportError:
        # If rembg is not installed, create a mock module
        import types

        mock_rembg = types.ModuleType("rembg")
        mock_rembg.remove = mock_remove  # type: ignore[attr-defined]
        mock_rembg.new_session = mock_new_session  # type: ignore[attr-defined]
        sys.modules["rembg"] = mock_rembg
