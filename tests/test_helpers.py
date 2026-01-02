"""Tests for 4-noks Elios4you helper functions.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from __future__ import annotations

import logging

# Direct imports using symlink (fournoks_elios4you -> 4noks_elios4you)
from custom_components.fournoks_elios4you.helpers import (
    host_valid,
    log_debug,
    log_error,
    log_info,
    log_warning,
)


class TestHostValid:
    """Tests for host_valid function."""

    def test_valid_ipv4(self) -> None:
        """Test valid IPv4 addresses."""
        assert host_valid("192.168.1.1") is True
        assert host_valid("10.0.0.1") is True
        assert host_valid("172.16.0.1") is True
        assert host_valid("255.255.255.255") is True

    def test_valid_hostname(self) -> None:
        """Test valid hostnames."""
        assert host_valid("localhost") is True
        assert host_valid("example.com") is True
        assert host_valid("my-device.local") is True
        assert host_valid("elios4you-device") is True

    def test_invalid_host(self) -> None:
        """Test invalid hosts."""
        assert host_valid("") is False
        assert host_valid("   ") is False
        assert host_valid("not a valid host!@#") is False
        assert host_valid("192.168.1.256") is False  # Invalid IP

    def test_none_host(self) -> None:
        """Test None host returns False."""
        assert host_valid(None) is False


class TestLoggingHelpers:
    """Tests for logging helper functions."""

    def test_log_debug(self, caplog) -> None:
        """Test log_debug formats correctly."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.DEBUG):
            log_debug(logger, "test_func", "Test message", key="value")

        assert "(test_func)" in caplog.text
        assert "Test message" in caplog.text
        assert "key=value" in caplog.text

    def test_log_info(self, caplog) -> None:
        """Test log_info formats correctly."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.INFO):
            log_info(logger, "test_func", "Info message")

        assert "(test_func)" in caplog.text
        assert "Info message" in caplog.text

    def test_log_info_with_kwargs(self, caplog) -> None:
        """Test log_info formats correctly with kwargs."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.INFO):
            log_info(logger, "test_func", "Info message", version="1.0.0")

        assert "(test_func)" in caplog.text
        assert "Info message" in caplog.text
        assert "version=1.0.0" in caplog.text

    def test_log_warning(self, caplog) -> None:
        """Test log_warning formats correctly."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.WARNING):
            log_warning(logger, "test_func", "Warning message", error="test error")

        assert "(test_func)" in caplog.text
        assert "Warning message" in caplog.text
        assert "error=test error" in caplog.text

    def test_log_error(self, caplog) -> None:
        """Test log_error formats correctly."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.ERROR):
            log_error(logger, "test_func", "Error message")

        assert "(test_func)" in caplog.text
        assert "Error message" in caplog.text

    def test_log_error_with_kwargs(self, caplog) -> None:
        """Test log_error formats correctly with kwargs."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.ERROR):
            log_error(logger, "test_func", "Error message", host="192.168.1.1")

        assert "(test_func)" in caplog.text
        assert "Error message" in caplog.text
        assert "host=192.168.1.1" in caplog.text

    def test_log_without_kwargs(self, caplog) -> None:
        """Test logging without extra kwargs."""
        logger = logging.getLogger("test")
        with caplog.at_level(logging.DEBUG):
            log_debug(logger, "test_func", "Simple message")

        assert "(test_func)" in caplog.text
        assert "Simple message" in caplog.text
        assert "[" not in caplog.text  # No kwargs bracket
