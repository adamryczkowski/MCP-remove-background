"""Unit tests for MCP tools.

Tests for the remove_background, list_background_models, unload_models,
and get_model_cache_status tools.
"""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from MCP_remove_background.constants import DEFAULT_MODEL, SUPPORTED_MODELS, UNLOAD_HINT
from MCP_remove_background.tools.remove_background import (
    CacheStatusOutput,
    ListModelsOutput,
    RemoveBackgroundOutput,
    UnloadModelsOutput,
    get_model_cache_status,
    list_background_models,
    remove_background,
    unload_models,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


@pytest.fixture
def sample_image_path() -> Generator[str, None, None]:
    """Create a temporary test image with white background and red center."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create a 100x100 image with white background
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Draw a red square in the center
        for x in range(25, 75):
            for y in range(25, 75):
                img.putpixel((x, y), (255, 0, 0))
        img.save(f.name)
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def mock_rembg(monkeypatch: "MonkeyPatch") -> None:
    """Mock rembg functions to avoid model downloads."""
    from tests.mocks.rembg_mock import apply_rembg_mocks

    apply_rembg_mocks(monkeypatch)


class TestRemoveBackgroundTool:
    """Tests for remove_background tool."""

    @pytest.mark.asyncio
    async def test_remove_background_requires_image_path(self) -> None:
        """TC-T01: Verify error when image_path is empty string."""
        # Empty string is technically provided but invalid
        result = await remove_background(image_path="")
        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is False
        assert result.error is not None
        # Error could be "not found", "is a directory", or other file-related error
        error_lower = result.error.lower()
        assert any(
            msg in error_lower
            for msg in ["not found", "is a directory", "failed", "invalid"]
        )

    @pytest.mark.asyncio
    async def test_remove_background_validates_model(self) -> None:
        """TC-T02: Verify error for invalid model."""
        result = await remove_background(
            image_path="/tmp/test.png",
            model="invalid-model",
        )
        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is False
        assert result.error is not None
        assert "invalid model" in result.error.lower()

    @pytest.mark.asyncio
    async def test_remove_background_handles_missing_file(self) -> None:
        """TC-T03: Verify error for missing file."""
        result = await remove_background(
            image_path="/nonexistent/path/to/image.png",
        )
        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_remove_background_output_schema(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-T04: Verify output matches expected schema."""
        result = await remove_background(image_path=sample_image_path)

        assert isinstance(result, RemoveBackgroundOutput)
        # Check all required fields are present
        assert hasattr(result, "success")
        assert hasattr(result, "input_path")
        assert hasattr(result, "output_path")
        assert hasattr(result, "file_size_bytes")
        assert hasattr(result, "method_used")
        assert hasattr(result, "model_used")
        assert hasattr(result, "error")

    @pytest.mark.asyncio
    async def test_remove_background_success_with_path(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-T05: Verify success with file path input."""
        result = await remove_background(image_path=sample_image_path)

        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is True
        assert result.error is None
        assert result.input_path == sample_image_path

    @pytest.mark.asyncio
    async def test_remove_background_returns_output_path(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-T06: Verify output_path is returned."""
        result = await remove_background(image_path=sample_image_path)

        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is True
        assert result.output_path is not None
        assert Path(result.output_path).exists()
        # Cleanup
        Path(result.output_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_remove_background_method_used_field(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-T07: Verify method_used field is populated."""
        result = await remove_background(image_path=sample_image_path)

        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is True
        assert result.method_used != ""
        # Should be either "floodfill" or a model name
        assert (
            result.method_used == "floodfill" or result.method_used in SUPPORTED_MODELS
        )
        # Cleanup
        if result.output_path:
            Path(result.output_path).unlink(missing_ok=True)


class TestListBackgroundModelsTool:
    """Tests for list_background_models tool."""

    def test_list_background_models_returns_output(self) -> None:
        """TC-T08: Verify list_models returns ListModelsOutput."""
        result = list_background_models()

        assert isinstance(result, ListModelsOutput)
        assert hasattr(result, "models")
        assert hasattr(result, "total_count")
        assert hasattr(result, "default_model")
        assert hasattr(result, "usage_hint")

    def test_list_background_models_includes_default(self) -> None:
        """TC-T09: Verify default model is indicated."""
        result = list_background_models()

        assert isinstance(result, ListModelsOutput)
        assert result.default_model == DEFAULT_MODEL
        # Verify default model is in the list
        model_ids = [m["id"] for m in result.models]
        assert DEFAULT_MODEL in model_ids

    def test_list_background_models_count(self) -> None:
        """TC-T10: Verify model count matches."""
        result = list_background_models()

        assert isinstance(result, ListModelsOutput)
        assert result.total_count == len(result.models)
        assert result.total_count == len(SUPPORTED_MODELS)
        # Verify all supported models are listed
        model_ids = [m["id"] for m in result.models]
        for model in SUPPORTED_MODELS:
            assert model in model_ids


class TestUnloadModelsTool:
    """Tests for unload_models tool."""

    def test_unload_models_returns_output(self) -> None:
        """Verify unload_models returns UnloadModelsOutput."""
        result = unload_models()

        assert isinstance(result, UnloadModelsOutput)
        assert hasattr(result, "success")
        assert hasattr(result, "models_unloaded")
        assert hasattr(result, "models_count")
        assert hasattr(result, "message")

    def test_unload_models_success_when_empty(self) -> None:
        """Verify unload_models succeeds even when no models are loaded."""
        result = unload_models()

        assert isinstance(result, UnloadModelsOutput)
        assert result.success is True
        assert result.models_count == 0
        assert result.models_unloaded == []

    def test_unload_models_message_is_string(self) -> None:
        """Verify unload_models returns a message string."""
        result = unload_models()

        assert isinstance(result, UnloadModelsOutput)
        assert isinstance(result.message, str)
        assert len(result.message) > 0


class TestGetModelCacheStatusTool:
    """Tests for get_model_cache_status tool."""

    def test_get_model_cache_status_returns_output(self) -> None:
        """Verify get_model_cache_status returns CacheStatusOutput."""
        result = get_model_cache_status()

        assert isinstance(result, CacheStatusOutput)
        assert hasattr(result, "loaded_models")
        assert hasattr(result, "models_count")
        assert hasattr(result, "idle_timeout")
        assert hasattr(result, "auto_unload_enabled")
        assert hasattr(result, "last_usage_time")
        assert hasattr(result, "time_until_unload")

    def test_get_model_cache_status_idle_timeout_positive(self) -> None:
        """Verify idle_timeout is a positive number."""
        result = get_model_cache_status()

        assert isinstance(result, CacheStatusOutput)
        assert result.idle_timeout >= 0

    def test_get_model_cache_status_auto_unload_enabled(self) -> None:
        """Verify auto_unload_enabled reflects idle_timeout setting."""
        result = get_model_cache_status()

        assert isinstance(result, CacheStatusOutput)
        # auto_unload_enabled should be True if idle_timeout > 0
        assert result.auto_unload_enabled == (result.idle_timeout > 0)

    def test_get_model_cache_status_loaded_models_is_list(self) -> None:
        """Verify loaded_models is a list."""
        result = get_model_cache_status()

        assert isinstance(result, CacheStatusOutput)
        assert isinstance(result.loaded_models, list)


class TestRemoveBackgroundHint:
    """Tests for the hint field in remove_background output."""

    @pytest.mark.asyncio
    async def test_remove_background_has_hint_field(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """Verify remove_background output has hint field."""
        result = await remove_background(image_path=sample_image_path)

        assert isinstance(result, RemoveBackgroundOutput)
        assert hasattr(result, "hint")
        # Cleanup
        if result.output_path:
            Path(result.output_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_remove_background_hint_when_ml_used(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """Verify hint is shown when ML model is used (not floodfill)."""
        # Disable floodfill to force ML model usage
        result = await remove_background(
            image_path=sample_image_path,
            try_floodfill_first=False,
        )

        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is True
        # When ML model is used, hint should be present
        assert result.method_used != "floodfill"
        assert result.hint == UNLOAD_HINT
        # Cleanup
        if result.output_path:
            Path(result.output_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_remove_background_no_hint_when_floodfill_used(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """Verify hint is None when floodfill is used."""
        # The sample image has uniform white background, so floodfill should work
        result = await remove_background(
            image_path=sample_image_path,
            try_floodfill_first=True,
        )

        assert isinstance(result, RemoveBackgroundOutput)
        assert result.success is True
        # When floodfill is used, hint should be None
        if result.method_used == "floodfill":
            assert result.hint is None
        # Cleanup
        if result.output_path:
            Path(result.output_path).unlink(missing_ok=True)
