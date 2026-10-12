"""Shared schemas and base client logic for external API services.

Includes common API response wrappers, error handling classes,
and an extensible HTTP client base for async service calls.
"""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Self

from httpx import AsyncClient, Response
from pydantic import BaseModel, Field

from nebula.core.config import HTTPConfig
from nebula.core.exceptions import ConfigurationError, RequestError
from nebula.core.transport import HTTPTransport
from nebula.models.base import SourceMetadata


class APIServiceResponse(BaseModel):
    """Base response schema for external API service calls.

    Captures both raw response metadata and extracted content.
    Used as a superclass for concrete API response types.

    Attributes
    ----------
    url : str
        Final URL of the response.
    content_type : str, optional
        Value of the `Content-Type` header.
    last_modified : datetime, optional
        Timestamp from `Last-Modified` HTTP header.
    encoding : str, optional
        Character encoding used to decode the response.
    content_encoding : str, optional
        HTTP-level content encoding (e.g., gzip).
    content_length : int, optional
        Size of the response body in bytes.
    text : str, optional
        Raw decoded body text, if available.
    response_json : dict, optional
        Parsed JSON dictionary from the response.

    Computed Properties
    -------------------
    data : Any
        Raw parsed data extracted from `response_json`.
    parsed_data : Any
        Additional processed data (e.g., model or DTO).

    """

    url: str = Field(..., description="The URL of the response")
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_type: str | None = Field(
        None, description="The content type of the response"
    )
    last_modified: datetime | None = Field(
        None, description="The last modified date of the response"
    )
    encoding: str | None = Field(
        None, description="The encoding of the response"
    )
    content_encoding: str | None = Field(
        None, description="The content encoding of the response"
    )
    content_length: int | None = Field(
        None, description="The content length of the response"
    )
    text: str | None = Field(None, description="The text of the response")
    response_json: dict | None = Field(
        None, description="The JSON data of the response"
    )

    _data: Any | None = None

    @property
    def data(self) -> Any:
        """Return the raw parsed data payload from the response.

        Typically extracted from `response_json` or from the raw response body
        by subclasses. Intended to provide structured data for internal use.

        Returns
        -------
        Any
            Parsed data, such as a dictionary or list.

        Raises
        ------
        NotImplementedError
            If the property is accessed on the base class directly.

        """
        raise NotImplementedError

    @data.setter
    def data(self, value: Any) -> None:
        """Set the raw parsed data payload.

        Typically called by subclasses after extracting relevant data
        from the HTTP response.

        Parameters
        ----------
        value : Any
            Structured data to store (e.g., dict, list, or model instance).

        """
        raise NotImplementedError

    _parsed_data: Any | None = None

    def source_metadata(self, source: str) -> SourceMetadata:
        """Return retrieval metadata separately from parsed content."""
        return SourceMetadata(
            source=source,
            url=self.url,
            retrieved_at=self.retrieved_at,
            last_modified=self.last_modified,
            content_type=self.content_type,
        )

    @property
    def parsed_data(self) -> Any:
        """Return enriched or post-processed response content.

        May involve additional transformation beyond raw `data`—such as
        parsing into domain-specific models, normalizing fields, or
        joining related records.

        Returns
        -------
        Any
            Final transformed representation of the response.

        Raises
        ------
        NotImplementedError
            If accessed on the base class without subclass override.

        """
        raise NotImplementedError

    @parsed_data.setter
    def parsed_data(self, value: Any) -> None:
        """Set the enriched or transformed version of response data.

        Often used to store domain-specific model instances or other
        final representations of the response payload.

        Parameters
        ----------
        value : Any
            Enriched or transformed response object.

        """
        raise NotImplementedError


class BaseClientError(RequestError):
    """Base exception raised when an API call fails.

    Attributes
    ----------
    message : str
        Human-readable error message.
    response : Response, optional
        Optional reference to the HTTPX `Response` object.

    """

    def __init__(self, message: str, response: Response | None = None):
        self.message = message
        super().__init__(self.message, response=response)


async def raise_on_4xx_5xx(response: Response) -> None:
    """Raise an exception on any HTTP 4xx or 5xx response.

    Used as an HTTPX event hook for error propagation.

    Parameters
    ----------
    response : Response
        HTTPX response object.

    Raises
    ------
    HTTPStatusError
        If response status code is 400 or above.

    """
    await response.aread()
    response.raise_for_status()


class BaseClient:
    """Async base client for interacting with external APIs.

    Coordinates a reusable transport for derived source clients.
    Requests use one pool during an async context and a temporary pool
    when a method is called on its own.

    Attributes
    ----------
    BASE_URL : str, optional
        Base URL for the API (must be set by subclasses).
    BASE_ERROR : Exception type
        Custom exception raised on API error.
    TIMEOUT : float
        Default request timeout in seconds.
    USER_AGENT : str
        Custom user-agent string for all requests.
    API_KEY : str, optional
        Optional API key to inject as `X-API-Key`.

    Raises
    ------
    ConfigurationError
        If `BASE_URL` is not provided at initialization.

    """

    BASE_URL: str | None = None
    BASE_ERROR: type[BaseClientError] = BaseClientError
    TIMEOUT: float = 30.0
    USER_AGENT: str = "nebula/0.1.0"
    API_KEY: str | None = None

    def __init__(
        self,
        *,
        config: HTTPConfig | None = None,
        http_client: AsyncClient | None = None,
        close_external_client: bool = False,
        BASE_URL: str | None = None,
        API_KEY: str | None = None,
        USER_AGENT: str | None = None,
        TIMEOUT: float | None = None,
    ) -> None:
        self.BASE_URL = BASE_URL or type(self).BASE_URL
        self.API_KEY = API_KEY if API_KEY is not None else type(self).API_KEY
        self.USER_AGENT = USER_AGENT or type(self).USER_AGENT
        self.TIMEOUT = TIMEOUT or type(self).TIMEOUT
        if self.BASE_URL is None:
            raise ConfigurationError("BASE_URL must be set")
        if config is None:
            config = HTTPConfig(timeout=self.TIMEOUT)
        self.config = config
        headers = {"User-Agent": self.USER_AGENT}
        if self.API_KEY is not None:
            headers["X-API-Key"] = self.API_KEY
        self._transport = HTTPTransport(
            config,
            client=http_client,
            close_external_client=close_external_client,
            headers=headers,
        )
        self._entered = False

    async def __aenter__(self) -> Self:
        """Open the reusable client for a source-client lifecycle."""
        _ = self._transport.client
        self._entered = True
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Release owned HTTP resources, including on cancellation."""
        self._entered = False
        await self._transport.close()

    async def aclose(self) -> None:
        """Release the owned HTTP client explicitly."""
        self._entered = False
        await self._transport.close()

    @property
    def _client(self) -> AbstractAsyncContextManager[AsyncClient]:
        """Borrow the active connection pool or open it for one call."""
        return self._client_context()

    @asynccontextmanager
    async def _client_context(self) -> AsyncIterator[AsyncClient]:
        if self._entered:
            yield self._transport.client
        else:
            try:
                yield self._transport.client
            finally:
                await self._transport.close()

    async def _perform_request(
        self,
        client: AsyncClient,
        method: str,
        path: str,
        **kwargs: Any | None,
    ) -> Response:
        """Perform an async HTTP request with error handling.

        Constructs and sends the request, raising a custom error
        on failure.

        Parameters
        ----------
        client : AsyncClient
            Configured HTTPX client instance.
        method : str
            HTTP method (e.g., "get", "post").
        path : str
            Path relative to the `BASE_URL`.
        **kwargs : Any
            Additional arguments forwarded to `httpx.AsyncClient.request`.

        Returns
        -------
        Response
            The HTTPX response object.

        Raises
        ------
        BASE_ERROR
            If the response has a 4xx or 5xx status.

        """
        url = (
            path
            if path.startswith(("https://", "http://"))
            else ((self.BASE_URL or "").rstrip("/") + "/" + path.lstrip("/"))
        )
        return await self._transport.request(
            client,
            method,
            url,
            source=type(self).__name__,
            **kwargs,
        )
