"""Tests for MCP Remove Background constants.

Test IDs from plan:
- TC-C01: test_default_model_is_u2net
- TC-C02: test_supported_models_list_not_empty
- TC-C03: test_supported_models_include_common_options
- TC-C04: test_default_color_threshold_reasonable
- TC-C05: test_min_uniform_border_percentage_valid
"""

from MCP_remove_background.constants import (
    DEFAULT_COLOR_THRESHOLD,
    DEFAULT_MODEL,
    MIN_UNIFORM_BORDER_PERCENTAGE,
    MODEL_METADATA,
    SUPPORTED_MODELS,
)


class TestDefaultModel:
    """Tests for default model configuration."""

    def test_default_model_is_u2net(self) -> None:
        """TC-C01: Verify default model is set to u2net."""
        assert DEFAULT_MODEL == "u2net"

    def test_default_model_in_supported_models(self) -> None:
        """Verify default model is in the supported models list."""
        assert DEFAULT_MODEL in SUPPORTED_MODELS


class TestSupportedModels:
    """Tests for supported models list."""

    def test_supported_models_list_not_empty(self) -> None:
        """TC-C02: Verify supported models list is populated."""
        assert len(SUPPORTED_MODELS) > 0

    def test_supported_models_include_common_options(self) -> None:
        """TC-C03: Verify common models are included."""
        required_models = [
            "u2net",
            "u2netp",
            "isnet-general-use",
            "isnet-anime",
            "birefnet-general",
        ]
        for model in required_models:
            assert model in SUPPORTED_MODELS, (
                f"Model {model} should be in SUPPORTED_MODELS"
            )

    def test_all_supported_models_have_metadata(self) -> None:
        """Verify all supported models have corresponding metadata."""
        for model in SUPPORTED_MODELS:
            assert model in MODEL_METADATA, f"Model {model} should have metadata"

    def test_model_metadata_has_required_fields(self) -> None:
        """Verify each model metadata has required fields."""
        required_fields = ["id", "name", "description", "size"]
        for model_id, metadata in MODEL_METADATA.items():
            for field in required_fields:
                assert field in metadata, f"Model {model_id} missing field {field}"


class TestFloodFillConfiguration:
    """Tests for flood-fill algorithm configuration."""

    def test_default_color_threshold_reasonable(self) -> None:
        """TC-C04: Verify flood-fill threshold is between 10-50."""
        assert 10 <= DEFAULT_COLOR_THRESHOLD <= 50

    def test_min_uniform_border_percentage_valid(self) -> None:
        """TC-C05: Verify border percentage is between 0.8-1.0."""
        assert 0.8 <= MIN_UNIFORM_BORDER_PERCENTAGE <= 1.0
