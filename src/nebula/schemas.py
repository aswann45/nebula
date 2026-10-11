"""Shared schemas and base client logic for external API services.

Includes common API response wrappers, error handling classes,
and an extensible HTTP client base for async service calls.
"""

from datetime import datetime
from typing import Any

from httpx import AsyncClient, HTTPStatusError, Response
from pydantic import BaseModel, Field, computed_field


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

    @computed_field  # type: ignore[prop-decorator]
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

    @computed_field  # type: ignore[prop-decorator]
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


class BaseClientError(Exception):
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
        self.response = response
        super().__init__(self.message)


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

    Provides standard retry, timeout, headers, and error-handling
    patterns for derived service clients. Designed to be subclassed.

    Attributes
    ----------
    BASE_URL : str, optional
        Base URL for the API (must be set by subclasses).
    BASE_ERROR : Exception type
        Custom exception raised on API error.
    TIMEOUT : int
        Default request timeout in seconds.
    USER_AGENT : str
        Custom user-agent string for all requests.
    API_KEY : str, optional
        Optional API key to inject as `X-API-Key`.

    Raises
    ------
    ValueError
        If `BASE_URL` is not provided at initialization.
    """

    BASE_URL: str | None = None
    BASE_ERROR: type[BaseClientError] = BaseClientError
    TIMEOUT: int = 10
    USER_AGENT: str = "constellation/1.0"
    API_KEY: str | None = None

    def __init__(self, **kwargs: Any | None):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if self.BASE_URL is None:
            raise ValueError("BASE_URL must be set")

    @property
    def _client(self) -> AsyncClient:
        """Create and configure an `httpx.AsyncClient` instance.

        Sets base URL, headers, timeout, and error hook.

        Returns
        -------
        AsyncClient
            Configured HTTPX client.
        """
        _client = AsyncClient(
            base_url=self.BASE_URL or "",
            timeout=self.TIMEOUT,
            event_hooks={"response": [raise_on_4xx_5xx]},
        )
        _client.headers["User-Agent"] = self.USER_AGENT
        if self.API_KEY is not None:
            _client.headers["X-API-Key"] = self.API_KEY
        return _client

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
        try:
            _method = method.lower()
            url: str = (self.BASE_URL or "") + path
            response: Response = await client.request(
                _method,
                url,
                **kwargs,  # type: ignore
            )
            return response
        except HTTPStatusError as exc:
            raise self.BASE_ERROR(
                f"{self.__class__.__name__} request failed:\n"
                f"{method.upper()} {url}\n"
                f"Exception: {exc!s}\n"
                f"Message: {exc.response is not None and exc.response.text}\n",
                response=exc.response,
            ) from None
