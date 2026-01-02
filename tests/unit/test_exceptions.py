"""Tests for MCP Remove Background exceptions.

Test IDs from plan:
- TC-E01: test_base_exception_inherits_from_exception
- TC-E02: test_invalid_request_error_message
- TC-E03: test_generation_error_message
- TC-E04: test_configuration_error_message
"""

import pytest

from MCP_remove_background.exceptions import (
    ConfigurationError,
    FileNotFoundError,
    GenerationError,
    InvalidRequestError,
    ModelNotFoundError,
    RemoveBackgroundError,
    UnsupportedFormatError,
)


class TestBaseException:
    """Tests for base exception class."""

    def test_base_exception_inherits_from_exception(self) -> None:
        """TC-E01: Verify base exception hierarchy."""
        assert issubclass(RemoveBackgroundError, Exception)

    def test_base_exception_can_be_raised(self) -> None:
        """Verify base exception can be raised and caught."""
        with pytest.raises(RemoveBackgroundError):
            raise RemoveBackgroundError("test error")

    def test_base_exception_stores_message(self) -> None:
        """Verify base exception stores the message."""
        error = RemoveBackgroundError("test message")
        assert str(error) == "test message"


class TestInvalidRequestError:
    """Tests for InvalidRequestError."""

    def test_invalid_request_error_message(self) -> None:
        """TC-E02: Verify InvalidRequestError stores message."""
        message = "Invalid parameter value"
        error = InvalidRequestError(message)
        assert str(error) == message

    def test_invalid_request_error_inherits_from_base(self) -> None:
        """Verify InvalidRequestError inherits from base exception."""
        assert issubclass(InvalidRequestError, RemoveBackgroundError)

    def test_invalid_request_error_can_be_caught_as_base(self) -> None:
        """Verify InvalidRequestError can be caught as base exception."""
        with pytest.raises(RemoveBackgroundError):
            raise InvalidRequestError("test")


class TestGenerationError:
    """Tests for GenerationError."""

    def test_generation_error_message(self) -> None:
        """TC-E03: Verify GenerationError stores message."""
        message = "Background removal failed"
        error = GenerationError(message)
        assert str(error) == message

    def test_generation_error_inherits_from_base(self) -> None:
        """Verify GenerationError inherits from base exception."""
        assert issubclass(GenerationError, RemoveBackgroundError)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error_message(self) -> None:
        """TC-E04: Verify ConfigurationError stores message."""
        message = "Invalid configuration"
        error = ConfigurationError(message)
        assert str(error) == message

    def test_configuration_error_inherits_from_base(self) -> None:
        """Verify ConfigurationError inherits from base exception."""
        assert issubclass(ConfigurationError, RemoveBackgroundError)


class TestFileNotFoundError:
    """Tests for FileNotFoundError."""

    def test_file_not_found_error_message(self) -> None:
        """Verify FileNotFoundError stores message."""
        message = "File not found: /path/to/file.png"
        error = FileNotFoundError(message)
        assert str(error) == message

    def test_file_not_found_error_inherits_from_base(self) -> None:
        """Verify FileNotFoundError inherits from base exception."""
        assert issubclass(FileNotFoundError, RemoveBackgroundError)


class TestUnsupportedFormatError:
    """Tests for UnsupportedFormatError."""

    def test_unsupported_format_error_message(self) -> None:
        """Verify UnsupportedFormatError stores message."""
        message = "Unsupported format: .bmp"
        error = UnsupportedFormatError(message)
        assert str(error) == message

    def test_unsupported_format_error_inherits_from_base(self) -> None:
        """Verify UnsupportedFormatError inherits from base exception."""
        assert issubclass(UnsupportedFormatError, RemoveBackgroundError)


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_model_not_found_error_message(self) -> None:
        """Verify ModelNotFoundError stores message."""
        message = "Model not found: unknown-model"
        error = ModelNotFoundError(message)
        assert str(error) == message

    def test_model_not_found_error_inherits_from_invalid_request(self) -> None:
        """Verify ModelNotFoundError inherits from InvalidRequestError."""
        assert issubclass(ModelNotFoundError, InvalidRequestError)

    def test_model_not_found_error_can_be_caught_as_base(self) -> None:
        """Verify ModelNotFoundError can be caught as base exception."""
        with pytest.raises(RemoveBackgroundError):
            raise ModelNotFoundError("test")
