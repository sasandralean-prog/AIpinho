from __future__ import annotations


class AIpinhoError(Exception):
    """Base error for AIpinho."""


class ConfigError(AIpinhoError):
    """Raised when configuration cannot be loaded or validated."""


class ConfigNotFoundError(ConfigError):
    """Raised when a required configuration file is missing."""


class ConfigEmptyError(ConfigError):
    """Raised when a required configuration file is empty."""


class ConfigValidationError(ConfigError):
    """Raised when a configuration file exists but is invalid."""


class UnsafePathError(AIpinhoError):
    """Raised when a path escapes its configured root."""
