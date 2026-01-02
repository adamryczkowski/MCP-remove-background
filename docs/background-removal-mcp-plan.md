# Background Removal MCP Server Plan

**Date:** 30 December 2025
**Status:** Draft - Pending Review
**Project:** MCP-remove-background

## Executive Summary

This document outlines the architecture and implementation plan for a dedicated MCP server that provides background removal functionality for images. The goal is to separate the dependency-heavy background removal functionality from the otherwise lightweight image generation MCP server (Imagen-MCP), effectively splitting the functionality into two specialized servers.

### Rationale for Separation

1. **Dependency Isolation:** Background removal requires heavy ML dependencies (rembg, onnxruntime, PyTorch models) that significantly increase installation size and complexity
2. **Resource Management:** ML models consume substantial memory (100MB-400MB per model) and benefit from dedicated session management
3. **Deployment Flexibility:** Allows independent scaling and deployment of background removal services
4. **Maintenance:** Easier to update and maintain specialized servers independently

---

## Research Findings

### Sources Consulted

1. **rembg GitHub** (https://github.com/danielgatis/rembg) - 21.4k stars, MIT License, v2.0.69
2. **BiRefNet GitHub** (https://github.com/ZhengPeng7/BiRefNet) - 3k stars, CAAI AIR'24 paper
3. **FastMCP GitHub** (https://github.com/jlowin/fastmcp) - 21.6k stars, Apache-2.0 License
4. **FastMCP Testing Documentation** (https://gofastmcp.com/patterns/testing)
5. **Existing Imagen-MCP Implementation** (local reference at /home/adam/tmp/Imagen-MCP)

### Technology Stack

| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| MCP Framework | FastMCP | ^2.3.0 | Pythonic MCP server framework |
| Background Removal | rembg | ^2.0.69 | MIT license, 1.1M downloads/month |
| ML Runtime | onnxruntime | ^1.19.0 | CPU by default, GPU optional |
| Image Processing | Pillow | ^11.0.0 | Image I/O and manipulation |
| Python | Python | >=3.12, <3.14 | Match rembg requirements |
| Testing | pytest-asyncio | ^0.25.0 | Async test support |

### Available Background Removal Models

| Model | Size | Use Case | Quality | Speed |
|-------|------|----------|---------|-------|
| `u2net` | 176MB | General purpose | Good | Medium |
| `u2netp` | 4MB | Lightweight/mobile | Moderate | Fast |
| `silueta` | 43MB | General (smaller) | Good | Medium |
| `isnet-general-use` | 176MB | General (newer) | Very Good | Medium |
| `isnet-anime` | 176MB | Anime/illustrations | Excellent for art | Medium |
| `birefnet-general` | 400MB | Best quality | Excellent | Slow |
| `birefnet-general-lite` | 100MB | Balanced | Very Good | Medium |
| `sam` | 400MB | Segment Anything | Excellent | Slow |

**Default Model:** `u2net` - Best balance of quality and compatibility

---

## Architecture Design

### Project Structure

```
MCP-remove-background/
├── MCP_remove_background/
│   ├── __init__.py
│   ├── cli.py                    # CLI entry point
│   ├── config.py                 # Configuration management
│   ├── constants.py              # Constants and type definitions
│   ├── exceptions.py             # Custom exceptions
│   ├── server.py                 # FastMCP server definition
│   ├── services/
│   │   ├── __init__.py
│   │   └── background_remover.py # Core background removal logic
│   ├── tools/
│   │   ├── __init__.py
│   │   └── remove_background.py  # MCP tool definitions
│   └── utils/
│       ├── __init__.py
│       └── file_utils.py         # File handling utilities
├── tests/
│   ├── conftest.py               # Pytest fixtures
│   ├── pytest.ini
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_background_remover.py
│   │   ├── test_constants.py
│   │   ├── test_exceptions.py
│   │   └── test_tools.py
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_server.py
│   └── mocks/
│       ├── __init__.py
│       └── rembg_mock.py
├── docs/
│   └── background-removal-mcp-plan.md
├── scripts/
│   ├── spack-ensure.sh
│   └── test-package.sh
├── pyproject.toml
├── justfile
├── README.md
└── spack.yaml
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  MCP Remove Background Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     FastMCP Server                          │ │
│  │  ┌─────────────────┐  ┌─────────────────┐                  │ │
│  │  │ remove_         │  │ list_           │                  │ │
│  │  │ background      │  │ models          │                  │ │
│  │  │ (tool)          │  │ (tool)          │                  │ │
│  │  └────────┬────────┘  └────────┬────────┘                  │ │
│  └───────────┼────────────────────┼────────────────────────────┘ │
│              │                    │                              │
│              ▼                    ▼                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Background Remover Service                     │ │
│  │                                                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐                  │ │
│  │  │  Flood-Fill     │  │  ML-Based       │                  │ │
│  │  │  Algorithm      │  │  (rembg)        │                  │ │
│  │  │  (fast path)    │  │  (fallback)     │                  │ │
│  │  └─────────────────┘  └─────────────────┘                  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              Session Cache (model reuse)             │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Tools

#### 1. `remove_background`

Remove background from an image file, producing PNG with transparency.

**Design Decision:** All image data is passed via file paths only. Base64-encoded binary data is explicitly NOT supported to keep API calls small and efficient. This is especially important for MCP servers where request/response sizes should be minimized.

**Input Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image_path` | `str` | Yes | - | Path to input image file |
| `output_path` | `str \| None` | No | `None` | Output path (auto-generated if not provided) |
| `model` | `str` | No | `u2net` | Background removal model to use |
| `alpha_matting` | `bool` | No | `False` | Enable alpha matting for smoother edges |
| `try_floodfill_first` | `bool` | No | `True` | Try fast flood-fill before ML |

**Output:**

```python
{
    "success": bool,
    "input_path": str,            # Path to input file
    "output_path": str,           # Path to output file with transparency
    "file_size_bytes": int,       # Size of output file
    "method_used": str,           # "floodfill" or model name
    "model_used": str,            # Model that was configured
    "error": str | None           # Error message if failed
}
```

#### 2. `list_background_models`

List all available background removal models.

**Input Parameters:** None

**Output:**

```python
{
    "models": [
        {
            "id": str,
            "name": str,
            "description": str,
            "size": str
        },
        ...
    ],
    "total_count": int,
    "default_model": str,
    "usage_hint": str
}
```

---

## Test-Driven Development Approach

The implementation will follow a strict TDD approach where tests are written before the implementation code. This ensures:

1. Clear specification of expected behavior
2. High test coverage from the start
3. Confidence in refactoring
4. Documentation through tests

### Test Categories

#### 1. Unit Tests

Unit tests focus on individual components in isolation, using mocks for external dependencies.

##### 1.1 Constants Tests (`tests/unit/test_constants.py`)

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| TC-C01 | `test_default_model_is_u2net` | Verify default model is set to `u2net` |
| TC-C02 | `test_supported_models_list_not_empty` | Verify supported models list is populated |
| TC-C03 | `test_supported_models_include_common_options` | Verify u2net, u2netp, isnet-general-use, isnet-anime, birefnet-general are included |
| TC-C04 | `test_default_color_threshold_reasonable` | Verify flood-fill threshold is between 10-50 |
| TC-C05 | `test_min_uniform_border_percentage_valid` | Verify border percentage is between 0.8-1.0 |

##### 1.2 Exceptions Tests (`tests/unit/test_exceptions.py`)

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| TC-E01 | `test_base_exception_inherits_from_exception` | Verify base exception hierarchy |
| TC-E02 | `test_invalid_request_error_message` | Verify InvalidRequestError stores message |
| TC-E03 | `test_generation_error_message` | Verify GenerationError stores message |
| TC-E04 | `test_configuration_error_message` | Verify ConfigurationError stores message |

##### 1.3 Background Remover Service Tests (`tests/unit/test_background_remover.py`)

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| TC-BR01 | `test_get_available_models_returns_list` | Verify models list is returned |
| TC-BR02 | `test_get_available_models_includes_default` | Verify default model is in list |
| TC-BR03 | `test_get_available_models_structure` | Verify each model has id, name, description, size |
| TC-BR04 | `test_get_session_caches_sessions` | Verify session caching works (mock rembg) |
| TC-BR05 | `test_get_session_rejects_invalid_model` | Verify InvalidRequestError for unknown model |
| TC-BR06 | `test_clear_session_cache_empties_cache` | Verify cache clearing works |
| TC-BR07 | `test_color_distance_identical_colors` | Verify distance is 0 for identical colors |
| TC-BR08 | `test_color_distance_different_colors` | Verify distance > 0 for different colors |
| TC-BR09 | `test_color_distance_symmetric` | Verify distance(a,b) == distance(b,a) |
| TC-BR10 | `test_get_border_pixels_returns_all_edges` | Verify all border pixels are returned |
| TC-BR11 | `test_get_border_pixels_count` | Verify correct count: 2*width + 2*height - 4 |
| TC-BR12 | `test_check_border_uniformity_uniform_image` | Verify uniform border detection |
| TC-BR13 | `test_check_border_uniformity_non_uniform` | Verify non-uniform border detection |
| TC-BR14 | `test_flood_fill_transparency_basic` | Verify flood-fill creates transparency |
| TC-BR15 | `test_flood_fill_preserves_foreground` | Verify foreground is not made transparent |
| TC-BR16 | `test_remove_background_floodfill_returns_none_for_complex` | Verify fallback to ML for complex images |
| TC-BR17 | `test_remove_background_from_file_success` | Verify file processing works (mock rembg) |
| TC-BR18 | `test_remove_background_from_file_invalid_model` | Verify error for invalid model |
| TC-BR19 | `test_remove_background_from_file_not_found` | Verify error for missing file |
| TC-BR20 | `test_remove_background_from_file_auto_output_path` | Verify auto-generated output path |
| TC-BR21 | `test_remove_background_from_file_creates_parent_dirs` | Verify parent directories are created |
| TC-BR22 | `test_remove_background_from_file_preserves_filename` | Verify output filename follows convention |

##### 1.4 Tools Tests (`tests/unit/test_tools.py`)

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| TC-T01 | `test_remove_background_requires_image_path` | Verify error when image_path not provided |
| TC-T02 | `test_remove_background_validates_model` | Verify error for invalid model |
| TC-T03 | `test_remove_background_handles_missing_file` | Verify error for missing file |
| TC-T04 | `test_remove_background_output_schema` | Verify output matches expected schema |
| TC-T05 | `test_remove_background_success_with_path` | Verify success with file path input |
| TC-T06 | `test_remove_background_returns_output_path` | Verify output_path is returned |
| TC-T07 | `test_remove_background_method_used_field` | Verify method_used field is populated |
| TC-T08 | `test_list_background_models_returns_dict` | Verify list_models returns dict |
| TC-T09 | `test_list_background_models_includes_default` | Verify default model is indicated |
| TC-T10 | `test_list_background_models_count` | Verify model count matches |

#### 2. Integration Tests

Integration tests verify the interaction between components and the MCP server.

##### 2.1 Server Tests (`tests/integration/test_server.py`)

| Test ID | Test Name | Description |
|---------|-----------|-------------|
| TC-S01 | `test_server_starts_successfully` | Verify server can be instantiated |
| TC-S02 | `test_server_has_remove_background_tool` | Verify tool is registered |
| TC-S03 | `test_server_has_list_models_tool` | Verify list_models tool is registered |
| TC-S04 | `test_remove_background_tool_callable` | Verify tool can be called via MCP client |
| TC-S05 | `test_list_models_tool_callable` | Verify list_models can be called via MCP client |
| TC-S06 | `test_server_handles_concurrent_requests` | Verify concurrent request handling |
| TC-S07 | `test_server_error_handling` | Verify errors are properly returned |

#### 3. Mock Strategy

To avoid downloading large ML models during testing, we use mocks:

##### 3.1 rembg Mock (`tests/mocks/rembg_mock.py`)

```python
# Mock for rembg.remove function
def mock_remove(image, session=None, **kwargs):
    """Return a simple RGBA image with transparent background."""
    # Create a copy of input with alpha channel
    return image.convert("RGBA")

# Mock for rembg.new_session function
def mock_new_session(model_name):
    """Return a mock session object."""
    return MockSession(model_name)
```

### Test Execution Order

Tests should be executed in this order to ensure proper TDD workflow:

1. **Phase 1: Constants and Exceptions** (no external dependencies)
   - `test_constants.py`
   - `test_exceptions.py`

2. **Phase 2: Core Service Logic** (with mocked rembg)
   - `test_background_remover.py`

3. **Phase 3: Tool Layer** (with mocked service)
   - `test_tools.py`

4. **Phase 4: Integration** (with mocked rembg)
   - `test_server.py`

---

## Implementation Plan

### Phase 1: Project Setup and Constants

**Duration:** 1 day

1. Update `pyproject.toml` with dependencies
2. Create `MCP_remove_background/constants.py`
3. Create `MCP_remove_background/exceptions.py`
4. Write and pass tests for constants and exceptions

**Deliverables:**
- [ ] `pyproject.toml` updated
- [ ] `constants.py` implemented
- [ ] `exceptions.py` implemented
- [ ] `tests/unit/test_constants.py` passing
- [ ] `tests/unit/test_exceptions.py` passing

### Phase 2: Background Remover Service

**Duration:** 2 days

1. Create `MCP_remove_background/services/background_remover.py`
2. Implement flood-fill algorithm
3. Implement ML-based removal (with rembg)
4. Implement session caching
5. Write and pass all service tests

**Deliverables:**
- [ ] `services/background_remover.py` implemented
- [ ] Flood-fill algorithm working
- [ ] rembg integration working
- [ ] Session caching working
- [ ] `tests/unit/test_background_remover.py` passing
- [ ] `tests/mocks/rembg_mock.py` implemented

### Phase 3: MCP Tools

**Duration:** 1 day

1. Create `MCP_remove_background/tools/remove_background.py`
2. Implement `remove_background` tool
3. Implement `list_background_models` tool
4. Write and pass all tool tests

**Deliverables:**
- [ ] `tools/remove_background.py` implemented
- [ ] `tests/unit/test_tools.py` passing

### Phase 4: Server Integration

**Duration:** 1 day

1. Create `MCP_remove_background/server.py`
2. Create `MCP_remove_background/cli.py`
3. Register tools with FastMCP
4. Write and pass integration tests

**Deliverables:**
- [ ] `server.py` implemented
- [ ] `cli.py` implemented
- [ ] `tests/integration/test_server.py` passing

### Phase 5: Documentation and Polish

**Duration:** 1 day

1. Update README.md
2. Add usage examples
3. Update justfile with new commands
4. Final validation

**Deliverables:**
- [ ] README.md updated
- [ ] `just validate` passing
- [ ] `just test` passing with coverage

---

## Dependencies

### Production Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.12"
fastmcp = "^2.3.0"
pydantic = "^2.10.0"
pydantic-settings = "^2.7.0"
click = "^8.1.0"
# Background removal dependencies
rembg = {version = "^2.0.69", extras = ["cpu"]}
pillow = "^11.0.0"
```

### Development Dependencies

```toml
[tool.poetry.group.dev.dependencies]
pre-commit = "^4.0.1"
pyright = "^1.1.405"

[tool.poetry.group.test.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.25.0"
coverage = "^7.6.0"
```

### Optional GPU Support

```toml
[tool.poetry.group.gpu]
optional = true

[tool.poetry.group.gpu.dependencies]
onnxruntime-gpu = "^1.19.0"
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Large model download on first use | High | Medium | Document in README, add model pre-download command |
| Slow processing on CPU | Medium | Medium | Document expected times, offer GPU option |
| Memory usage spikes | Medium | Low | Session reuse, lazy loading |
| Model accuracy issues | Low | Medium | Offer multiple models, document best practices |
| ONNX Runtime compatibility | Low | High | Pin versions, test on CI |
| rembg API changes | Low | Medium | Pin version, monitor releases |

---

## Design Decisions

### 1. File-Path-Only API

**Decision:** All image data is passed via file paths only. No base64-encoded binary data.

**Rationale:**
- MCP API calls should be small and efficient
- Large binary data in requests/responses causes performance issues
- File paths allow for streaming and memory-efficient processing
- Consistent with Unix philosophy of file-based I/O

### 2. Flood-Fill First Strategy

**Decision:** Attempt flood-fill algorithm before ML-based approach.

**Rationale:**
- Flood-fill is 10-100x faster than ML models
- Works well for AI-generated images with solid backgrounds
- Falls back to ML only when needed
- Reduces resource usage for simple cases

### 3. Session Caching

**Decision:** Cache rembg sessions for model reuse.

**Rationale:**
- Model loading is expensive (1-5 seconds)
- Cached sessions enable fast subsequent requests
- Memory is freed on server shutdown

### 4. Default Model Selection

**Decision:** Use `u2net` as the default model.

**Rationale:**
- Good balance of quality and speed
- Widely tested and stable
- Reasonable model size (176MB)
- Works well for general-purpose use

---

## Appendix

### A. Sample Code

#### A.1 Basic Usage

```python
from MCP_remove_background.services.background_remover import (
    remove_background_from_file,
)

# Remove background from a file
output_path, method = remove_background_from_file(
    input_path="input.png",
    output_path="output.png",
    model="u2net",
)
print(f"Saved to {output_path} using {method}")
```

#### A.2 MCP Tool Call

```python
# Via MCP client
result = await client.call_tool(
    "remove_background",
    {
        "image_path": "/path/to/input.png",
        "output_path": "/path/to/output.png",
        "model": "isnet-anime",
    }
)
```

### B. Test Fixture Example

```python
# tests/conftest.py
import pytest
from PIL import Image
import tempfile
import os

@pytest.fixture
def sample_image_path():
    """Create a temporary test image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # Create a simple 100x100 image with white background
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Draw a red square in the center
        for x in range(25, 75):
            for y in range(25, 75):
                img.putpixel((x, y), (255, 0, 0))
        img.save(f.name)
        yield f.name
    os.unlink(f.name)

@pytest.fixture
def mock_rembg(monkeypatch):
    """Mock rembg functions to avoid model downloads."""
    from tests.mocks.rembg_mock import mock_remove, mock_new_session

    monkeypatch.setattr("rembg.remove", mock_remove)
    monkeypatch.setattr("rembg.new_session", mock_new_session)
```

### C. References

1. **rembg Documentation:** https://github.com/danielgatis/rembg
2. **FastMCP Documentation:** https://gofastmcp.com/
3. **BiRefNet Paper:** CAAI AIR'24 - Bilateral Reference for High-Resolution Dichotomous Image Segmentation
4. **ONNX Runtime:** https://onnxruntime.ai/
5. **Pillow Documentation:** https://pillow.readthedocs.io/

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-30 | 0.1.0 | Initial plan draft |

---

*End of Document*
