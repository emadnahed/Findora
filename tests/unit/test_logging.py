"""Tests for the logging module."""



from src.core.logging import (
    add_request_id,
    bind_request_context,
    clear_request_context,
    get_logger,
    request_id_var,
    setup_logging,
)


class TestRequestIdVar:
    """Tests for request_id context variable."""

    def test_request_id_var_default_is_none(self) -> None:
        """Test that request_id_var defaults to None."""
        clear_request_context()
        assert request_id_var.get() is None

    def test_request_id_var_can_be_set(self) -> None:
        """Test that request_id_var can be set."""
        request_id_var.set("test-123")
        assert request_id_var.get() == "test-123"
        clear_request_context()


class TestAddRequestId:
    """Tests for add_request_id processor."""

    def test_add_request_id_when_set(self) -> None:
        """Test that request_id is added when set."""
        request_id_var.set("req-456")
        event_dict: dict[str, str] = {"event": "test"}

        result = add_request_id(None, "info", event_dict)

        assert result["request_id"] == "req-456"
        assert result["event"] == "test"
        clear_request_context()

    def test_add_request_id_when_not_set(self) -> None:
        """Test that request_id is not added when not set."""
        clear_request_context()
        event_dict: dict[str, str] = {"event": "test"}

        result = add_request_id(None, "info", event_dict)

        assert "request_id" not in result
        assert result["event"] == "test"


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_json_format(self) -> None:
        """Test setup_logging with JSON format."""
        setup_logging(log_level="INFO", log_format="json")

        # Verify structlog is configured
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_console_format(self) -> None:
        """Test setup_logging with console format."""
        setup_logging(log_level="DEBUG", log_format="console")

        # Verify structlog is configured
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_different_levels(self) -> None:
        """Test setup_logging with different log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            setup_logging(log_level=level, log_format="json")
            logger = get_logger("test")
            assert logger is not None


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self) -> None:
        """Test getting a logger with a specific name."""
        logger = get_logger("my_module")
        assert logger is not None

    def test_get_logger_without_name(self) -> None:
        """Test getting a logger without a name."""
        logger = get_logger()
        assert logger is not None

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test that get_logger returns a BoundLogger."""
        logger = get_logger("test")
        # Check it has logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")


class TestBindRequestContext:
    """Tests for bind_request_context function."""

    def test_bind_request_context_sets_request_id(self) -> None:
        """Test that bind_request_context sets the request_id."""
        bind_request_context(request_id="test-789")

        assert request_id_var.get() == "test-789"
        clear_request_context()

    def test_bind_request_context_with_extra_kwargs(self) -> None:
        """Test bind_request_context with additional kwargs."""
        bind_request_context(request_id="test-abc", method="GET", path="/test")

        assert request_id_var.get() == "test-abc"
        clear_request_context()


class TestClearRequestContext:
    """Tests for clear_request_context function."""

    def test_clear_request_context_resets_request_id(self) -> None:
        """Test that clear_request_context resets request_id to None."""
        request_id_var.set("test-xyz")
        assert request_id_var.get() == "test-xyz"

        clear_request_context()

        assert request_id_var.get() is None

    def test_clear_request_context_clears_contextvars(self) -> None:
        """Test that clear_request_context clears structlog contextvars."""
        bind_request_context(request_id="test-123", extra="data")

        clear_request_context()

        assert request_id_var.get() is None
