"""Tests for MCP Remove Background background_remover service.

Test IDs from plan:
- TC-BR01: test_get_available_models_returns_list
- TC-BR02: test_get_available_models_includes_default
- TC-BR03: test_get_available_models_structure
- TC-BR04: test_get_session_caches_sessions
- TC-BR05: test_get_session_rejects_invalid_model
- TC-BR06: test_clear_session_cache_empties_cache
- TC-BR07: test_color_distance_identical_colors
- TC-BR08: test_color_distance_different_colors
- TC-BR09: test_color_distance_symmetric
- TC-BR10: test_get_border_pixels_returns_all_edges
- TC-BR11: test_get_border_pixels_count
- TC-BR12: test_check_border_uniformity_uniform_image
- TC-BR13: test_check_border_uniformity_non_uniform
- TC-BR14: test_flood_fill_transparency_basic
- TC-BR15: test_flood_fill_preserves_foreground
- TC-BR16: test_remove_background_floodfill_returns_none_for_complex
- TC-BR17: test_remove_background_from_file_success
- TC-BR18: test_remove_background_from_file_invalid_model
- TC-BR19: test_remove_background_from_file_not_found
- TC-BR20: test_remove_background_from_file_auto_output_path
- TC-BR21: test_remove_background_from_file_creates_parent_dirs
- TC-BR22: test_remove_background_from_file_preserves_filename
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from MCP_remove_background.constants import DEFAULT_MODEL, SUPPORTED_MODELS
from MCP_remove_background.exceptions import (
    FileNotFoundError as FileNotFoundErr,
    InvalidRequestError,
)
from MCP_remove_background.services.background_remover import (
    check_border_uniformity,
    clear_session_cache,
    color_distance,
    flood_fill_transparency,
    get_available_models,
    get_border_pixels,
    get_session,
    remove_background_floodfill,
    remove_background_from_file,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def sample_uniform_image() -> Image.Image:
    """Create a test image with uniform white background and red center."""
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    # Draw a red square in the center
    for x in range(25, 75):
        for y in range(25, 75):
            img.putpixel((x, y), (255, 0, 0))
    return img


@pytest.fixture
def sample_non_uniform_image() -> Image.Image:
    """Create a test image with non-uniform border colors."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    # Make left border red
    for y in range(100):
        img.putpixel((0, y), (255, 0, 0))
    # Make right border blue
    for y in range(100):
        img.putpixel((99, y), (0, 0, 255))
    return img


@pytest.fixture
def sample_image_path(sample_uniform_image: Image.Image) -> str:
    """Create a temporary test image file."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        sample_uniform_image.save(f.name)
        return f.name


@pytest.fixture
def mock_rembg(monkeypatch: "MonkeyPatch") -> None:
    """Mock rembg functions to avoid model downloads."""
    from tests.mocks.rembg_mock import apply_rembg_mocks

    apply_rembg_mocks(monkeypatch)


class TestGetAvailableModels:
    """Tests for get_available_models function."""

    def test_get_available_models_returns_list(self) -> None:
        """TC-BR01: Verify models list is returned."""
        models = get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_get_available_models_includes_default(self) -> None:
        """TC-BR02: Verify default model is in list."""
        models = get_available_models()
        model_ids = [m["id"] for m in models]
        assert DEFAULT_MODEL in model_ids

    def test_get_available_models_structure(self) -> None:
        """TC-BR03: Verify each model has id, name, description, size."""
        models = get_available_models()
        required_fields = ["id", "name", "description", "size"]
        for model in models:
            for field in required_fields:
                assert field in model, f"Model missing field: {field}"


class TestGetSession:
    """Tests for get_session function."""

    def test_get_session_caches_sessions(
        self, mock_rembg: None, monkeypatch: "MonkeyPatch"
    ) -> None:
        """TC-BR04: Verify session caching works."""
        # Clear cache first
        clear_session_cache()

        # Import the module to access the cache
        from MCP_remove_background.services import background_remover

        # Get session twice
        session1 = get_session("u2net")
        session2 = get_session("u2net")

        # Should be the same cached session
        assert session1 is session2
        assert "u2net" in background_remover._session_cache

    def test_get_session_rejects_invalid_model(self) -> None:
        """TC-BR05: Verify InvalidRequestError for unknown model."""
        with pytest.raises(InvalidRequestError) as exc_info:
            get_session("invalid-model-name")
        assert "Unsupported" in str(exc_info.value)

    def test_clear_session_cache_empties_cache(
        self, mock_rembg: None, monkeypatch: "MonkeyPatch"
    ) -> None:
        """TC-BR06: Verify cache clearing works."""
        from MCP_remove_background.services import background_remover

        # Create a session
        get_session("u2net")
        assert len(background_remover._session_cache) > 0

        # Clear cache
        clear_session_cache()
        assert len(background_remover._session_cache) == 0


class TestColorDistance:
    """Tests for color_distance function."""

    def test_color_distance_identical_colors(self) -> None:
        """TC-BR07: Verify distance is 0 for identical colors."""
        color = (128, 128, 128)
        assert color_distance(color, color) == 0.0

    def test_color_distance_different_colors(self) -> None:
        """TC-BR08: Verify distance > 0 for different colors."""
        white = (255, 255, 255)
        black = (0, 0, 0)
        assert color_distance(white, black) > 0

    def test_color_distance_symmetric(self) -> None:
        """TC-BR09: Verify distance(a,b) == distance(b,a)."""
        color1 = (100, 150, 200)
        color2 = (50, 100, 150)
        assert color_distance(color1, color2) == color_distance(color2, color1)


class TestGetBorderPixels:
    """Tests for get_border_pixels function."""

    def test_get_border_pixels_returns_all_edges(self) -> None:
        """TC-BR10: Verify all border pixels are returned."""
        img = Image.new("RGB", (10, 10), color=(255, 255, 255))
        border_pixels = get_border_pixels(img)

        # Check corners are included
        assert (0, 0) in border_pixels
        assert (9, 0) in border_pixels
        assert (0, 9) in border_pixels
        assert (9, 9) in border_pixels

        # Check edges are included
        assert (5, 0) in border_pixels  # Top edge
        assert (5, 9) in border_pixels  # Bottom edge
        assert (0, 5) in border_pixels  # Left edge
        assert (9, 5) in border_pixels  # Right edge

    def test_get_border_pixels_count(self) -> None:
        """TC-BR11: Verify correct count: 2*width + 2*height - 4."""
        width, height = 20, 15
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        border_pixels = get_border_pixels(img)

        expected_count = 2 * width + 2 * height - 4
        assert len(border_pixels) == expected_count


class TestCheckBorderUniformity:
    """Tests for check_border_uniformity function."""

    def test_check_border_uniformity_uniform_image(
        self, sample_uniform_image: Image.Image
    ) -> None:
        """TC-BR12: Verify uniform border detection."""
        is_uniform, median_color = check_border_uniformity(sample_uniform_image)
        assert is_uniform is True
        assert median_color is not None
        # Should be close to white (255, 255, 255)
        assert median_color[0] > 250
        assert median_color[1] > 250
        assert median_color[2] > 250

    def test_check_border_uniformity_non_uniform(
        self, sample_non_uniform_image: Image.Image
    ) -> None:
        """TC-BR13: Verify non-uniform border detection."""
        is_uniform, _ = check_border_uniformity(sample_non_uniform_image)
        assert is_uniform is False


class TestFloodFillTransparency:
    """Tests for flood_fill_transparency function."""

    def test_flood_fill_transparency_basic(
        self, sample_uniform_image: Image.Image
    ) -> None:
        """TC-BR14: Verify flood-fill creates transparency."""
        background_color = (255, 255, 255)
        result = flood_fill_transparency(sample_uniform_image, background_color)

        assert result.mode == "RGBA"
        # Check that some pixels are transparent
        pixels = result.load()
        assert pixels is not None
        # Corner should be transparent (was white background)
        assert pixels[0, 0][3] == 0

    def test_flood_fill_preserves_foreground(
        self, sample_uniform_image: Image.Image
    ) -> None:
        """TC-BR15: Verify foreground is not made transparent."""
        background_color = (255, 255, 255)
        result = flood_fill_transparency(sample_uniform_image, background_color)

        pixels = result.load()
        assert pixels is not None
        # Center should be opaque (was red foreground)
        assert pixels[50, 50][3] == 255


class TestRemoveBackgroundFloodfill:
    """Tests for remove_background_floodfill function."""

    def test_remove_background_floodfill_returns_none_for_complex(
        self, sample_non_uniform_image: Image.Image
    ) -> None:
        """TC-BR16: Verify fallback to ML for complex images."""
        result = remove_background_floodfill(sample_non_uniform_image)
        assert result is None


class TestRemoveBackgroundFromFile:
    """Tests for remove_background_from_file function."""

    def test_remove_background_from_file_success(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-BR17: Verify file processing works."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = f.name

        result_path, method = remove_background_from_file(
            sample_image_path, output_path=output_path
        )

        assert Path(result_path).exists()
        assert method in ["floodfill", *SUPPORTED_MODELS]

        # Cleanup
        Path(result_path).unlink(missing_ok=True)

    def test_remove_background_from_file_invalid_model(
        self, sample_image_path: str
    ) -> None:
        """TC-BR18: Verify error for invalid model."""
        # This test should fail at model validation before file processing
        # We need to disable floodfill to trigger model validation
        with pytest.raises(InvalidRequestError):
            remove_background_from_file(
                sample_image_path,
                model="invalid-model",
                try_floodfill_first=False,
            )

    def test_remove_background_from_file_not_found(self) -> None:
        """TC-BR19: Verify error for missing file."""
        with pytest.raises(FileNotFoundErr):
            remove_background_from_file("/nonexistent/path/to/image.png")

    def test_remove_background_from_file_auto_output_path(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-BR20: Verify auto-generated output path."""
        result_path, _ = remove_background_from_file(sample_image_path)

        assert "_nobg" in result_path
        assert result_path.endswith(".png")
        assert Path(result_path).exists()

        # Cleanup
        Path(result_path).unlink(missing_ok=True)

    def test_remove_background_from_file_creates_parent_dirs(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-BR21: Verify parent directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "output.png"

            result_path, _ = remove_background_from_file(
                sample_image_path, output_path=str(output_path)
            )

            assert Path(result_path).exists()
            assert Path(result_path).parent.exists()

    def test_remove_background_from_file_preserves_filename(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-BR22: Verify output filename follows convention."""
        input_path = Path(sample_image_path)
        result_path, _ = remove_background_from_file(sample_image_path)

        result_name = Path(result_path).stem
        expected_suffix = "_nobg"

        assert result_name.endswith(expected_suffix)
        assert result_name.replace(expected_suffix, "") == input_path.stem

        # Cleanup
        Path(result_path).unlink(missing_ok=True)
