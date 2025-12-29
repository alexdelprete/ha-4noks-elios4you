"""Helper utilities for 4-noks Elios4You integration.

This module provides common utility functions used across the integration,
including standardized logging helpers that provide consistent formatting
and context information.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

import ipaddress
import logging
import re
from typing import Any


def host_valid(host: str | None) -> bool:
    """Validate if hostname or IP address is valid.

    Checks if the provided string is a valid IPv4/IPv6 address or a valid hostname
    according to standard naming conventions.

    Args:
        host: The hostname or IP address to validate

    Returns:
        bool: True if valid hostname or IP address, False otherwise

    Example:
        host_valid("192.168.1.1")  # True
        host_valid("example.com")  # True
        host_valid("invalid host!")  # False
        host_valid("192.168.1.256")  # False (invalid IP octet)
        host_valid(None)  # False

    """
    if host is None:
        return False

    try:
        # Check if it's a valid IP address (IPv4 or IPv6)
        return ipaddress.ip_address(host).version in (4, 6)
    except ValueError:
        # Not a valid IP address, validate as hostname
        # First, check if it looks like an IP address (all numeric parts)
        # If so, it's invalid since ip_address() already rejected it
        parts = host.split(".")
        if all(part.isdigit() for part in parts):
            return False
        # Validate as hostname - only alphanumeric and hyphens allowed in labels
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in parts)


def log_debug(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized debug logging with context.

    Provides consistent debug logging format across the integration with
    optional context parameters for better debugging.

    Args:
        logger: Logger instance to use for logging
        context: Context string (e.g., function/method name)
        message: Log message
        **kwargs: Additional context data to include in the log

    Example:
        log_debug(_LOGGER, "async_setup", "Setting up integration", domain=DOMAIN)
        # Output: (async_setup) [domain=sensor]: Setting up integration

    """
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.debug("%s: %s", context_str, message)


def log_info(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized info logging with context.

    Provides consistent info logging format across the integration with
    optional context parameters.

    Args:
        logger: Logger instance to use for logging
        context: Context string (e.g., function/method name)
        message: Log message
        **kwargs: Additional context data to include in the log

    Example:
        log_info(_LOGGER, "async_setup", "Integration loaded", version="1.0.0")
        # Output: (async_setup) [version=1.0.0]: Integration loaded

    """
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.info("%s: %s", context_str, message)


def log_warning(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized warning logging with context.

    Provides consistent warning logging format across the integration with
    optional context parameters.

    Args:
        logger: Logger instance to use for logging
        context: Context string (e.g., function/method name)
        message: Log message
        **kwargs: Additional context data to include in the log

    Example:
        log_warning(_LOGGER, "validate_config", "Invalid port", port=99999)
        # Output: (validate_config) [port=99999]: Invalid port

    """
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.warning("%s: %s", context_str, message)


def log_error(logger: logging.Logger, context: str, message: str, **kwargs: Any) -> None:
    """Standardized error logging with context.

    Provides consistent error logging format across the integration with
    optional context parameters for better error tracking.

    Args:
        logger: Logger instance to use for logging
        context: Context string (e.g., function/method name)
        message: Log message
        **kwargs: Additional context data to include in the log

    Example:
        log_error(_LOGGER, "connect", "Connection failed", host="192.168.1.1")
        # Output: (connect) [host=192.168.1.1]: Connection failed

    """
    context_str = f"({context})"
    if kwargs:
        context_parts = [f"{k}={v}" for k, v in kwargs.items()]
        context_str += f" [{', '.join(context_parts)}]"
    logger.error("%s: %s", context_str, message)
