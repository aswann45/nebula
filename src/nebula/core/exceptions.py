"""Errors shared by source clients.

Message text intentionally excludes query strings and response bodies.
"""

from httpx import Response


class NebulaError(Exception):
    """Base error for the public Nebula API."""


class ConfigurationError(NebulaError):
    """Invalid client or transport configuration."""


class RequestError(NebulaError):
    """An HTTP request failed."""

    def __init__(
        self,
        message: str,
        *,
        source: str | None = None,
        method: str | None = None,
        url: str | None = None,
        response: Response | None = None,
    ) -> None:
        """Attach safe source and request context to a failure."""
        self.source = source
        self.method = method
        self.url = url
        self.response = response
        super().__init__(message)


class AuthenticationError(RequestError):
    """Authentication or authorization was rejected."""


class RateLimitError(RequestError):
    """The source rejected a request due to rate limiting."""


class ResourceNotFoundError(RequestError):
    """The requested resource does not exist."""


class SourceUnavailableError(RequestError):
    """The source or network is temporarily unavailable."""


class ParsingError(NebulaError):
    """A source document could not be parsed."""


class DataValidationError(NebulaError):
    """A source document failed validation."""


class StorageError(NebulaError):
    """Persistence failed."""
