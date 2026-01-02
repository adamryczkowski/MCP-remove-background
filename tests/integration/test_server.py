"""Integration tests for MCP Remove Background server.

Tests for the FastMCP server and tool registration.
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from MCP_remove_background.server import mcp

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


class TestServerStartup:
    """Tests for server startup and instantiation."""

    def test_server_starts_successfully(self) -> None:
        """TC-S01: Verify server can be instantiated."""
        # The mcp object should be a FastMCP instance
        assert mcp is not None
        assert hasattr(mcp, "run")
        assert hasattr(mcp, "tool")
        # Server name should be set
        assert mcp.name == "Background Removal MCP Server"

    def test_server_has_remove_background_tool(self) -> None:
        """TC-S02: Verify remove_background tool is registered."""
        # Get registered tools
        tools = mcp._tool_manager._tools
        tool_names = list(tools.keys())

        assert "remove_background" in tool_names

    def test_server_has_list_models_tool(self) -> None:
        """TC-S03: Verify list_background_models tool is registered."""
        # Get registered tools
        tools = mcp._tool_manager._tools
        tool_names = list(tools.keys())

        assert "list_background_models" in tool_names


class TestToolCallability:
    """Tests for tool callability via MCP server."""

    @pytest.mark.asyncio
    async def test_remove_background_tool_callable(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-S04: Verify remove_background tool can be called via MCP."""
        # Get the tool function
        tools = mcp._tool_manager._tools
        remove_bg_tool = tools["remove_background"]

        # Call the tool function directly
        # pyright doesn't know about .fn attribute on Tool class
        result = await remove_bg_tool.fn(image_path=sample_image_path)  # type: ignore[attr-defined]

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["input_path"] == sample_image_path
        assert result["output_path"] is not None

        # Cleanup
        if result["output_path"]:
            Path(result["output_path"]).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_list_models_tool_callable(self) -> None:
        """TC-S05: Verify list_background_models can be called via MCP."""
        # Get the tool function
        tools = mcp._tool_manager._tools
        list_models_tool = tools["list_background_models"]

        # Call the tool function directly
        # pyright doesn't know about .fn attribute on Tool class
        result = list_models_tool.fn()  # type: ignore[attr-defined]

        assert isinstance(result, dict)
        assert "models" in result
        assert "total_count" in result
        assert "default_model" in result
        assert result["total_count"] > 0


class TestConcurrencyAndErrors:
    """Tests for concurrent request handling and error handling."""

    @pytest.mark.asyncio
    async def test_server_handles_concurrent_requests(
        self, sample_image_path: str, mock_rembg: None
    ) -> None:
        """TC-S06: Verify concurrent request handling."""
        # Get the tool function
        tools = mcp._tool_manager._tools
        remove_bg_tool = tools["remove_background"]

        # Create multiple concurrent requests
        async def call_tool() -> dict:
            # pyright doesn't know about .fn attribute on Tool class
            return await remove_bg_tool.fn(image_path=sample_image_path)  # type: ignore[attr-defined]

        # Run 3 concurrent requests
        results = await asyncio.gather(
            call_tool(),
            call_tool(),
            call_tool(),
        )

        # All should succeed
        assert len(results) == 3
        for result in results:
            assert isinstance(result, dict)
            assert result["success"] is True

        # Cleanup
        for result in results:
            if result.get("output_path"):
                Path(result["output_path"]).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_server_error_handling(self) -> None:
        """TC-S07: Verify errors are properly returned."""
        # Get the tool function
        tools = mcp._tool_manager._tools
        remove_bg_tool = tools["remove_background"]

        # Call with invalid file path
        # pyright doesn't know about .fn attribute on Tool class
        result = await remove_bg_tool.fn(image_path="/nonexistent/path.png")  # type: ignore[attr-defined]

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] is not None
        assert "not found" in result["error"].lower()
