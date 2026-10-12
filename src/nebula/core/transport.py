"""Reusable asynchronous HTTP transport for source clients."""

import asyncio
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from .config import HTTPConfig
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
    RequestError,
    ResourceNotFoundError,
    SourceUnavailableError,
)

_RETRY_STATUSES = {429, 502, 503, 504}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def safe_url(url: str) -> str:
    """Strip credentials, query values, and fragments from a URL."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def parse_http_date(value: str | None) -> datetime | None:
    """Parse an RFC 7231 HTTP date, including obsolete accepted forms."""
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class HTTPTransport:
    """Own or borrow one HTTPX client and bound concurrent requests."""

    def __init__(
        self,
        config: HTTPConfig,
        *,
        client: httpx.AsyncClient | None = None,
        close_external_client: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Configure an owned or externally managed HTTPX client."""
        self.config = config
        self._external_client = client
        self._close_external_client = close_external_client
        self._client: httpx.AsyncClient | None = client
        self._headers = headers or {}
        self._semaphore = asyncio.Semaphore(config.max_concurrency)

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the current client, opening an owned client if needed."""
        if self._external_client is not None:
            if self._external_client.is_closed:
                raise ConfigurationError("The supplied HTTP client is closed")
            return self._external_client
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_connections=self.config.max_connections
                ),
                headers=self._headers,
            )
        return self._client

    async def close(self) -> None:
        """Close an owned client and optionally an external one."""
        if self._client is not None and (
            self._external_client is None or self._close_external_client
        ):
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        source: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Issue a bounded request with safe retries and typed errors."""
        method = method.upper()
        display_url = safe_url(url)
        request_options = dict(kwargs)
        request_options["headers"] = {
            **self._headers,
            **(kwargs.get("headers") or {}),
        }
        request_options.setdefault("timeout", self.config.timeout)
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self._semaphore:
                    response = await client.request(
                        method, url, **request_options
                    )
            except httpx.RequestError:
                if (
                    method in _SAFE_METHODS
                    and attempt < self.config.max_retries
                ):
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                raise SourceUnavailableError(
                    f"{source} {method} {display_url}: network failure",
                    source=source,
                    method=method,
                    url=display_url,
                ) from None
            if response.status_code < 400:
                return response
            if (
                method in _SAFE_METHODS
                and response.status_code in _RETRY_STATUSES
                and attempt < self.config.max_retries
            ):
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue
            error_type: type[RequestError]
            if response.status_code in {401, 403}:
                error_type = AuthenticationError
            elif response.status_code == 404:
                error_type = ResourceNotFoundError
            elif response.status_code == 429:
                error_type = RateLimitError
            elif response.status_code >= 500:
                error_type = SourceUnavailableError
            else:
                error_type = RequestError
            raise error_type(
                f"{source} {method} {display_url}: "
                f"HTTP {response.status_code}",
                source=source,
                method=method,
                url=display_url,
                response=response,
            )
        raise AssertionError("request loop exhausted")

    def _backoff(self, attempt: int) -> float:
        return float(
            self.config.backoff_factor
            * (2**attempt)
            * random.uniform(0.5, 1.5)
        )

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        guidance = response.headers.get("Retry-After")
        if guidance:
            try:
                return max(0.0, float(guidance))
            except ValueError:
                date = parse_http_date(guidance)
                if date is not None:
                    return max(
                        0.0,
                        (date - datetime.now(UTC)).total_seconds(),
                    )
        return self._backoff(attempt)
