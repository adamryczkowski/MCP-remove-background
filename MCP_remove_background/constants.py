"""Constants for MCP Remove Background Server."""

from typing import Literal

# Default model for background removal
DEFAULT_MODEL = "u2net"

# Supported background removal models with their metadata
SUPPORTED_MODELS = [
    "u2net",  # General purpose (176MB)
    "u2netp",  # Lightweight (4MB)
    "silueta",  # General, smaller (43MB)
    "isnet-general-use",  # General, newer (176MB)
    "isnet-anime",  # Anime/illustrations (176MB)
    "birefnet-general",  # Best quality (400MB)
    "birefnet-general-lite",  # Balanced (100MB)
    "sam",  # Segment Anything Model (400MB)
]

# Model metadata for list_background_models tool
MODEL_METADATA = {
    "u2net": {
        "id": "u2net",
        "name": "U2-Net",
        "description": "General purpose background removal model",
        "size": "176MB",
    },
    "u2netp": {
        "id": "u2netp",
        "name": "U2-Net Portrait",
        "description": "Lightweight model optimized for mobile/fast processing",
        "size": "4MB",
    },
    "silueta": {
        "id": "silueta",
        "name": "Silueta",
        "description": "General purpose model with smaller footprint",
        "size": "43MB",
    },
    "isnet-general-use": {
        "id": "isnet-general-use",
        "name": "IS-Net General",
        "description": "Newer general purpose model with improved accuracy",
        "size": "176MB",
    },
    "isnet-anime": {
        "id": "isnet-anime",
        "name": "IS-Net Anime",
        "description": "Optimized for anime and illustration images",
        "size": "176MB",
    },
    "birefnet-general": {
        "id": "birefnet-general",
        "name": "BiRefNet General",
        "description": "Highest quality model for professional results",
        "size": "400MB",
    },
    "birefnet-general-lite": {
        "id": "birefnet-general-lite",
        "name": "BiRefNet Lite",
        "description": "Balanced quality and speed for general use",
        "size": "100MB",
    },
    "sam": {
        "id": "sam",
        "name": "Segment Anything Model",
        "description": "Meta's Segment Anything Model for versatile segmentation",
        "size": "400MB",
    },
}

# Type alias for background model
BackgroundModel = Literal[
    "u2net",
    "u2netp",
    "silueta",
    "isnet-general-use",
    "isnet-anime",
    "birefnet-general",
    "birefnet-general-lite",
    "sam",
]

# Flood-fill algorithm configuration
# Color distance threshold for considering pixels as "same color" (0-255 scale)
DEFAULT_COLOR_THRESHOLD = 30

# Minimum percentage of border pixels that must be uniform for flood-fill to work
MIN_UNIFORM_BORDER_PERCENTAGE = 0.9

# Output file naming
OUTPUT_SUFFIX = "_nobg"
OUTPUT_FORMAT = "PNG"

# Model auto-unload configuration
# Time in seconds after which idle models are unloaded to conserve RAM
# Default: 300 seconds (5 minutes). Set to 0 to disable auto-unload.
DEFAULT_MODEL_IDLE_TIMEOUT = 300

# Hint message to remind users to unload models after use
UNLOAD_HINT = (
    "Tip: ML models consume significant RAM. Call 'unload_models' tool "
    "when done processing images to free memory."
)
