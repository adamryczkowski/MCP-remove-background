# MCP Remove Background Server

A Model Context Protocol (MCP) server for removing backgrounds from images using AI-powered segmentation models.

## Features

- **Background Removal**: Remove backgrounds from images using AI-powered segmentation
  - Multiple model options optimized for different image types
  - Outputs PNG with full alpha transparency
  - Fast flood-fill algorithm for simple backgrounds (optional)
- **Model Catalog**: Access comprehensive information about all available background removal models

## Supported Models

| Model | Size | Best For | Quality |
|-------|------|----------|---------|
| `u2net` | 176MB | General purpose (default) | Good |
| `u2netp` | 4MB | Lightweight/mobile | Moderate |
| `silueta` | 43MB | General, smaller footprint | Good |
| `isnet-general-use` | 176MB | General, newer | Very Good |
| `isnet-anime` | 176MB | Anime/illustrations | Excellent for art |
| `birefnet-general` | 400MB | Best quality | Excellent |
| `birefnet-general-lite` | 100MB | Balanced | Very Good |
| `sam` | 400MB | Segment Anything | Excellent |

## Installation

### Option 1: Install with pipx (Recommended for CLI usage)

```bash
# Install directly from the repository
pipx install git+https://github.com/your-username/MCP-remove-background.git

# Or install from local directory
cd MCP-remove-background
pipx install .

# Run the server
mcp-remove-background
```

### Option 2: Install with Poetry (Recommended for development)

```bash
# Clone the repository
git clone <repository-url>
cd MCP-remove-background

# Install dependencies with Poetry
just setup

# Run the server
poetry run mcp-remove-background
# Or
poetry run python -m MCP_remove_background.server
```

### Option 3: Install with pip

```bash
# Install from the repository
pip install git+https://github.com/your-username/MCP-remove-background.git

# Or install from local directory
pip install .

# Run the server
mcp-remove-background
```

## Usage

### Running the Server

```bash
# If installed with pipx or pip
mcp-remove-background

# If using Poetry (development)
poetry run mcp-remove-background

# Alternative: run as Python module
poetry run python -m MCP_remove_background.server

# With FastMCP CLI (more options)
poetry run fastmcp run MCP_remove_background/server.py --transport http --port 8000
```

### CLI Options

When using the `fastmcp run` command, you have additional options:

| Option | Description |
|--------|-------------|
| `--transport`, `-t` | Transport protocol: `stdio` (default), `http`, `sse`, `streamable-http` |
| `--host` | Host to bind to (default: 127.0.0.1) |
| `--port`, `-p` | Port for HTTP/SSE transport (default: 8000) |
| `--log-level`, `-l` | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `--no-banner` | Don't show the server banner |

### MCP Client Configuration

To use this MCP server with an AI agent, add the following configuration to your MCP client.

#### Claude Desktop (pipx installation)

If you installed with pipx, add to your Claude Desktop configuration file (`~/.config/claude/claude_desktop_config.json` on Linux, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "remove-background": {
      "command": "mcp-remove-background"
    }
  }
}
```

#### Claude Desktop (Poetry installation)

If you're using Poetry for development:

```json
{
  "mcpServers": {
    "remove-background": {
      "command": "poetry",
      "args": ["run", "mcp-remove-background"],
      "cwd": "/path/to/MCP-remove-background"
    }
  }
}
```

#### Cline / Roo Code

Add to your VS Code settings or Cline MCP configuration:

```json
{
  "mcpServers": {
    "remove-background": {
      "command": "mcp-remove-background"
    }
  }
}
```

#### Generic MCP Client (Copy-Paste Ready)

For pipx/pip installation:

```json
{
  "remove-background": {
    "command": "mcp-remove-background"
  }
}
```

For Poetry installation:

```json
{
  "remove-background": {
    "command": "poetry",
    "args": ["run", "mcp-remove-background"],
    "cwd": "/path/to/MCP-remove-background"
  }
}
```

**Configuration Options:**

| Field | Description |
|-------|-------------|
| `command` | The command to run (`poetry` for Poetry-managed projects) |
| `args` | Command arguments to start the MCP server |
| `cwd` | Working directory - set to your MCP-remove-background installation path |

**Important:** Replace `/path/to/MCP-remove-background` with the actual path to your installation.

## Tools

### `remove_background`

Remove the background from an image, replacing it with transparency.

**Parameters:**
- `image_path` (required): Path to the image file to process
- `output_path` (optional): Path for the output PNG file (auto-generated if not specified)
- `model` (optional): Background removal model (default: "u2net")
- `alpha_matting` (optional): Enable alpha matting for smoother edges (default: false)
- `try_floodfill_first` (optional): Try fast flood-fill before ML (default: true)

**Returns:**
- `success`: Whether background removal succeeded
- `input_path`: Path to the input file
- `output_path`: Path to the output PNG file with transparency
- `file_size_bytes`: Size of the output file in bytes
- `method_used`: "floodfill" or model name
- `model_used`: The model that was configured
- `error`: Error message if removal failed

**Example:**
```python
result = await remove_background(
    image_path="/path/to/image.png",
    model="isnet-anime"
)
if result["success"]:
    print(f"Transparent image saved to: {result['output_path']}")
```

### `list_background_models`

List all available background removal models with their descriptions.

**Parameters:** None

**Returns:**
- `models`: List of available models with id, name, description, and size
- `total_count`: Number of available models
- `default_model`: The default model used when not specified
- `usage_hint`: How to use the model parameter

**Example Response:**
```json
{
  "models": [
    {
      "id": "u2net",
      "name": "U2-Net",
      "description": "General purpose background removal model",
      "size": "176MB"
    },
    ...
  ],
  "total_count": 8,
  "default_model": "u2net",
  "usage_hint": "Pass model='model_id' to remove_background tool"
}
```

## Development

### Setup

```bash
# Initialize the development environment
just setup
```

### Running Tests

```bash
# Run all tests with coverage
just test

# Run specific test file
poetry run pytest tests/unit/test_constants.py -v
```

### Code Quality

```bash
# Run formatting
just format

# Run all pre-commit hooks (includes formatting, linting, type-checking)
just validate

# Run type checking only
just typecheck
```

### Building

```bash
# Build wheel package
just package

# Test the built package
just test-package

# Clean build artifacts
just clean
```

### Available Just Commands

| Command | Description |
|---------|-------------|
| `just setup` | Initialize development environment (Poetry deps + pre-commit hooks) |
| `just test` | Run unit tests with coverage report |
| `just typecheck` | Run static type checking with pyright |
| `just format` | Run formatting hooks (ruff, etc.) |
| `just validate` | Run all pre-commit hooks on all files |
| `just package` | Build wheel package into dist/ |
| `just test-package` | Build, install, and smoke-test the package |
| `just clean` | Clean build artifacts and temporary files |
| `just recreate-venv` | Recreate virtual environment with specific Python version |
| `just serve-http` | Run MCP server with HTTP transport (shared mode) |
| `just mcp-status` | Check if MCP HTTP server is running |

### Project Structure

```
MCP-remove-background/
├── MCP_remove_background/
│   ├── __init__.py              # Package exports
│   ├── cli.py                   # CLI entry point
│   ├── config.py                # Configuration management
│   ├── constants.py             # Constants and type definitions
│   ├── exceptions.py            # Custom exceptions
│   ├── server.py                # FastMCP server definition
│   ├── services/
│   │   └── background_remover.py # Core background removal logic
│   ├── tools/
│   │   └── remove_background.py  # MCP tool definitions
│   └── utils/
│       └── file_utils.py         # File handling utilities
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── pytest.ini
│   ├── unit/
│   │   ├── test_constants.py
│   │   ├── test_exceptions.py
│   │   ├── test_background_remover.py
│   │   └── test_tools.py
│   ├── integration/
│   │   └── test_server.py
│   └── mocks/
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

## Spack Integration

This project uses [Spack](https://spack.io/) to manage system-level dependencies (like the Python interpreter). Spack is automatically installed to `~/.local/share/spack` if not already available.

To manually activate the Spack environment:

```bash
source .spack-activate.sh
```

To update Spack packages:

```bash
spack -e . concretize --fresh-roots --force
spack -e . install
```

## License

MIT License
