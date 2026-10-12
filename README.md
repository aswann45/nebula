# Nebula

Nebula retrieves data from Congress.gov, the House and Senate clerks, the
Congressional Legislators GitHub dataset, and OMB apportionments. This is
the Phase 1 transport update; the existing source clients and response
wrappers remain the public interface.

## HTTP client lifecycle

```python
from nebula.github_congress.client import GitHubCongressClient
from nebula.core.config import HTTPConfig

async with GitHubCongressClient(
    config=HTTPConfig(timeout=20, max_concurrency=4)
) as client:
    members = await client.get_current_member_data()
    committees = await client.get_current_committee_data()
```

The context manager reuses one HTTP connection pool across calls and closes
it on exit. A method can also be called without a context manager; its
temporary pool is then closed after that call. All source clients accept an
external `httpx.AsyncClient` as `http_client`. Nebula leaves that client open
unless `close_external_client=True` is supplied.

`HTTPConfig` validates timeout, connection, concurrency, and retry limits.
Transient GET failures are retried with jittered exponential backoff, and
`Retry-After` is honored for retryable responses. Errors in
`nebula.core.exceptions` include source, method, and URL path, with query
values omitted from messages. Missing House roll calls and OMB files keep
their previous `None` result; other request failures raise typed errors.

Congress.gov requires `API_KEY` (or `CONGRESS_GOV_API_KEY` in settings).
For example, use `CongressGovClient(API_KEY="...")` inside an async context.

OMB collection still returns the existing response-wrapper list. Its HTML
index links are resolved against the OMB host, deduplicated, and downloaded
with at most `max_concurrency` workers. Typed OMB models and independent
parsers are planned for Phase 2.
