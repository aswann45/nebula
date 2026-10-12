# Nebula

Nebula retrieves data from Congress.gov, the House and Senate clerks, the
Congressional Legislators GitHub dataset, and OMB apportionments. The
existing source clients and response wrappers remain available alongside
new typed parsing and retrieval methods.

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
with at most `max_concurrency` workers.

## Typed records and local parsing

Phase 2 adds independent parsers for OMB JSON and HTML, House and Senate
XML, Congress.gov JSON, and congressional YAML. Parsers accept bytes, so a
local file can be validated without an HTTP connection:

```python
from pathlib import Path
from nebula.omb_apportionments.parsers import OMBApportionmentParser

record = OMBApportionmentParser().parse(Path("apportionment.json").read_bytes())
print(record.schedule_data[0].approved_amount)
```

The new typed retrieval methods include
`OMBApportionmentsClient.get_apportionment_model()`,
`HouseClerkClient.get_roll_call_vote_model()`, and
`GitHubCongressClient.get_current_members()`. Existing methods retain their
response-wrapper returns. The OMB wrapper's legacy `parsed_data` property
still uses `schedue_data`; the validated `OMBApportionment` model uses
`schedule_data`.

Source records retain additional published fields. OMB monetary amounts use
`Decimal`, and account codes and period-of-availability values remain text.
The new House roll-call model preserves the original vote metadata alongside
normalized fields. Converting a source record to a small canonical domain
record can omit source details, so keep the source model when full fidelity
matters. Public model serialization does not trigger parsing or network work.
