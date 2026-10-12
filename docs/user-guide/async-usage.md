# Async usage and lifecycle

Use `async with` for a series of requests. It reuses one HTTPX connection
pool and closes it after success, failure, or cancellation.

```python
from nebula.core.config import HTTPConfig
from nebula.github_congress.client import GitHubCongressClient

async with GitHubCongressClient(
    config=HTTPConfig(max_concurrency=4)
) as client:
    members = await client.get_current_members()
    committees = await client.get_current_committees()
```

A standalone method call creates a temporary pool. Direct clients accept
`http_client=...` to use an existing `httpx.AsyncClient`; Nebula does not
close that external client unless `close_external_client=True` is requested.
`Nebula(clients={"house_clerk": client})` injects a client into the facade.

The HTTP transport bounds active requests. Collection workers also have a
configured concurrency limit. Requests may be retried for transient network
failures and HTTP 429, 502, 503, and 504, with `Retry-After` respected when
present. See the [exceptions](../api/exceptions.md) for error types.
