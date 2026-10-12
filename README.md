# Nebula

Nebula retrieves data from Congress.gov, the House and Senate clerks, the
Congressional Legislators GitHub dataset, and OMB apportionments. The
existing source clients and response wrappers remain available alongside
new typed parsing and retrieval methods.

## Domain API

```python
from nebula import Nebula

async with Nebula() as nebula:
    senators = await nebula.members.list(chamber="senate")
    committees = await nebula.committees.current()
    vote = await nebula.votes.house(2026, 125)
    references = await nebula.apportionments.list()
    if references:
        record = await nebula.apportionments.get(references[0].url)
```

The facade creates source clients when first used and closes their owned
HTTP connections on exit. `Nebula(config=HTTPConfig(...))` sets transport
limits; `Nebula(clients={"house_clerk": client})` accepts an existing source
client for dependency injection. Use `await nebula.get_source(name)` for
direct access to a registered client. The source registry lists each
adapter's supported domains through `nebula.sources.capabilities(name)`.

Members also support Congress.gov lookup with `members.get(bioguide_id)`
and bounded `members.get_many(ids)`, historical GitHub members with
`members.historical(year)`, and the current House and Senate Clerk rosters.
OMB's `apportionments.collect()` returns validated records using the
existing bounded source retrieval. It omits missing files and raises on
other source failures. Legislation has no supported retrieval operation yet;
the current Congress.gov bill and amendment methods remain unimplemented.

## Command-line interface

Installing the package creates the `nebula` command. The CLI uses the same
domain services as the Python API:

```bash
nebula --help
nebula --version
nebula sources list --format json
nebula sources status
nebula sources status --check
nebula config show
nebula config validate
nebula members get B000490 --format json
nebula members list --chamber house --format jsonl
nebula members historical --year 2020
nebula members house-current
nebula members senate-current
nebula committees current
nebula votes house --year 2026 --roll-call 125
nebula votes house --year 2026 --format jsonl
nebula apportionments list
nebula apportionments get https://apportionment-public.max.gov/file.json
nebula apportionments collect --fiscal-year 2026 --output ./data/omb/
```

`sources status` reports local configuration without making a request.
`--check` explicitly probes each source over HTTP and reports reachability
separately from credential availability. `config show` masks secrets.

Every retrieval command accepts `--format table|json|jsonl|csv`, `--output`,
`--overwrite`, `--quiet`, and `--verbose`. Collection output defaults to JSONL.
When `--output` names a directory or ends in `/`, Nebula writes a
deterministically named file there. Existing files require `--overwrite`.
Nested CSV fields are encoded as compact JSON strings in their cells.
Machine-readable stdout contains only records; diagnostics and interactive
collection progress go to stderr.

Exit codes are 0 for success, 2 for invalid arguments, 3 for configuration
errors, 4 for network or missing-resource errors, 5 for parsing or data
validation errors, 6 for partial collections, and 7 for output errors.
Partial-collection reporting will become available with resumable collection.

The OMB fiscal-year filter checks validated records after retrieval, so it
currently downloads every listed JSON file. House year retrieval checks
roll numbers through the Clerk index's listed maximum and skips missing
files; checkpointing and streaming are not available yet.

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

Congress.gov reads `CONGRESS_GOV_API_KEY` from the environment or a `.env`
file in the working directory. Environment variables take precedence. Copy
`.env.example` to `.env` and replace the example value, or pass
`CongressGovClient(API_KEY="...")` directly. The settings class also accepts
injected credentials for testing.

OMB collection still returns the existing response-wrapper list. Its HTML
index links are resolved against the OMB host, deduplicated, and downloaded
with at most `max_concurrency` workers.

## Typed records and local parsing

Independent parsers cover OMB JSON and HTML, House and Senate XML,
Congress.gov JSON, and congressional YAML. Parsers accept bytes, so a
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

Source records retain additional published fields. OMB monetary amounts are
whole-number integers; fractional amounts fail validation. Account codes and
period-of-availability values remain text.
The new House roll-call model preserves the original vote metadata alongside
normalized fields. Converting a source record to a small canonical domain
record can omit source details, so keep the source model when full fidelity
matters. Public model serialization does not trigger parsing or network work.
