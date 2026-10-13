"""Regression coverage for the transport and source clients."""

import asyncio
import contextlib
import io
import unittest
from datetime import UTC, datetime
from email.utils import format_datetime

import httpx
from pydantic import ValidationError

from nebula.core.config import HTTPConfig
from nebula.core.exceptions import (
    RateLimitError,
    ResourceNotFoundError,
    SourceUnavailableError,
)
from nebula.github_congress.client import GitHubCongressClient
from nebula.house_clerk.client import HouseClerkClient
from nebula.omb_apportionments.client import OMBApportionmentsClient
from nebula.senate_clerk.client import SenateClerkClient


class TransportTests(unittest.IsolatedAsyncioTestCase):
    """Verify transport behavior with local HTTPX mock handlers."""

    async def test_retries_and_redacts_query(self) -> None:
        """Retry transient responses and omit credentials from errors."""
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls < 3:
                return httpx.Response(503)
            return httpx.Response(200, text="ok")

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = GitHubCongressClient(
            http_client=http,
            config=HTTPConfig(max_retries=2, backoff_factor=0),
        )
        async with client:
            result = await client._perform_request(
                http, "GET", "/test?api_key=secret"
            )
        self.assertEqual(result.text, "ok")
        self.assertEqual(calls, 3)
        self.assertFalse(http.is_closed)
        await http.aclose()

    async def test_status_errors_and_no_secret(self) -> None:
        """Map statuses to typed exceptions without URL query values."""
        for status, error in (
            (404, ResourceNotFoundError),
            (429, RateLimitError),
            (503, SourceUnavailableError),
        ):
            http = httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request, code=status: httpx.Response(code)
                )
            )
            client = GitHubCongressClient(
                http_client=http,
                config=HTTPConfig(max_retries=0),
            )
            with self.assertRaises(error) as raised:
                await client._perform_request(
                    http, "GET", "/test?api_key=secret"
                )
            self.assertNotIn("secret", str(raised.exception))
            await http.aclose()

    async def test_connection_reuse_and_http_date(self) -> None:
        """Reuse an external client and parse the HTTP date as UTC."""
        seen: list[int] = []
        modified = format_datetime(
            datetime(2026, 10, 1, tzinfo=UTC), usegmt=True
        )

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(id(request))
            return httpx.Response(
                200,
                text="[]",
                headers={"Last-Modified": modified},
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = GitHubCongressClient(http_client=http)
        async with client:
            first = await client.get_current_member_data()
            second = await client.get_current_member_data()
        self.assertEqual(len(seen), 2)
        self.assertEqual(first.last_modified, second.last_modified)
        self.assertEqual(first.last_modified.tzinfo, UTC)  # type: ignore[union-attr]
        self.assertFalse(http.is_closed)
        await http.aclose()

    async def test_retry_after_and_headers(self) -> None:
        """Honor retry guidance and apply headers to external clients."""
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if len(seen) == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = GitHubCongressClient(
            http_client=http,
            USER_AGENT="nebula-test",
            config=HTTPConfig(max_retries=1, backoff_factor=0),
        )
        await client._perform_request(http, "GET", "/x")
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0].headers["User-Agent"], "nebula-test")
        await http.aclose()

    async def test_timeout_and_cancellation(self) -> None:
        """Wrap timeouts and release an opted-in client on cancellation."""

        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("secret", request=request)

        http = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
        client = GitHubCongressClient(
            http_client=http, config=HTTPConfig(max_retries=0)
        )
        with self.assertRaises(SourceUnavailableError) as raised:
            await client._perform_request(http, "GET", "/x?key=secret")
        self.assertNotIn("secret", str(raised.exception))
        await http.aclose()

        async def slow(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(10)
            return httpx.Response(200)

        injected = httpx.AsyncClient(transport=httpx.MockTransport(slow))
        owned = GitHubCongressClient(
            http_client=injected,
            close_external_client=True,
            config=HTTPConfig(max_retries=0),
        )
        async with owned:
            task = asyncio.create_task(
                owned._perform_request(injected, "GET", "/x")
            )
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(injected.is_closed)

    async def test_validation_and_no_library_output(self) -> None:
        """Reject invalid settings and keep library calls silent."""
        with self.assertRaises(ValidationError):
            HTTPConfig(max_concurrency=0)
        with self.assertRaises(TypeError):
            GitHubCongressClient(random_attribute=True)  # type: ignore[call-arg]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="[]")

        output = io.StringIO()
        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with contextlib.redirect_stdout(output):
            for source in (
                GitHubCongressClient,
                HouseClerkClient,
                SenateClerkClient,
            ):
                client = source(http_client=http)
                await client.get_current_member_data()
        self.assertEqual(output.getvalue(), "")
        await http.aclose()

    async def test_bounded_omb_downloads(self) -> None:
        """Limit simultaneous OMB downloads to the configured count."""
        active = 0
        peak = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal active, peak
            if request.url.path == "/":
                links = "".join(
                    f'<a href="/file{i}.json">{i}</a>' for i in range(9)
                )
                return httpx.Response(200, text=links)
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return httpx.Response(200, json={"FileId": "1"})

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = OMBApportionmentsClient(
            http_client=http,
            config=HTTPConfig(max_concurrency=2),
        )
        result = await client.get_apportionments_data()
        self.assertEqual(len(result), 9)
        self.assertLessEqual(peak, 2)
        self.assertFalse(http.is_closed)
        await http.aclose()

    async def test_omb_missing_and_transient_are_distinct(self) -> None:
        """Keep 404 as None while surfacing unavailable resources."""

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/":
                return httpx.Response(
                    200,
                    text='<a href="/missing.json">a</a>'
                    '<a href="/unavailable.json">b</a>',
                )
            if request.url.path == "/missing.json":
                return httpx.Response(404)
            return httpx.Response(503)

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = OMBApportionmentsClient(
            http_client=http, config=HTTPConfig(max_retries=0)
        )
        with self.assertRaises(SourceUnavailableError):
            await client.get_apportionments_data()
        await http.aclose()
