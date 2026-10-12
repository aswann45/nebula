# Working on Nebula

Nebula is a Python 3.11+ library for retrieving and validating government
and legislative data. This file is a quick orientation for future changes.
The checked-out code is authoritative; consult `README.md` and `docs/` for
user-facing behavior and the current list of unimplemented features.

## Project map

- `src/nebula/core/`: validated HTTP configuration, reusable HTTPX
  transport, retries, and typed errors.
- `src/nebula/{congress_gov,house_clerk,senate_clerk,github_congress,omb_apportionments}/`:
  the five direct source clients, parsers, source models, and legacy wrappers.
- `src/nebula/models/`: shared domain models and normalization helpers.
- `src/nebula/services/`: domain operations; `src/nebula/api.py` owns the
  lifecycle-aware `Nebula` facade.
- `src/nebula/sources/registry.py`: explicit source registration and
  capability declarations.
- `src/nebula/collection/` and `src/nebula/storage/`: bounded discovery,
  retrieval, checkpointing, provenance, and filesystem persistence. OMB is
  the current integrated example.
- `src/nebula/cli/`: Typer commands that delegate to services, with shared
  rendering and error handling.
- `tests/`: tests grouped by component, using local fixtures and mocked
  HTTP; `docs/` and `mkdocs.yml`: the documentation site.

## Design and compatibility rules

- Preserve public imports and working methods, including `nebula.schemas`,
  `nebula.typings`, and all five direct source-client packages. Add typed
  methods or forwarding wrappers when a return-type change would break
  callers. Do not create a second implementation of the same operation.
- Keep HTTP retrieval in source clients, byte parsing in independent
  parsers, domain coordination in services, and presentation in the CLI.
  Constructors must not make network requests. Use `async with` for shared
  client lifecycles and leave injected HTTPX clients open by default.
- Use Pydantic v2 for public data contracts and Pydantic Settings for
  credentials. `CONGRESS_GOV_API_KEY` comes from the environment or a local
  `.env` file. Never log or expose secrets or query values in errors.
- OMB approved amounts are whole-number integers. Keep account and agency
  identifiers as text when leading zeroes matter. The typed model uses
  `schedule_data`; the legacy wrapper retains `schedue_data` for callers.
- Bulk requests must be bounded. Preserve partial successes and checkpoint
  progress on failure or cancellation. Do not assume that source IDs are
  contiguous or that index order is stable.
- Keep changes incremental. Avoid placeholder operations, unnecessary
  abstractions, and phase labels in code or docs. Use feature-focused branch
  names. Clean up style issues in older files when touching them.

## Development checks

Use Poetry 2.4+ and the lock file:

```bash
poetry install --with dev,ruff,docs
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest -q
poetry run mkdocs build --strict
poetry build
```

The repository uses a 79-character line limit and NumPy-style public
docstrings. Add tests beside the relevant component, not under phase names.
Ordinary tests must remain offline; use fixtures and `httpx.MockTransport`.
When changing packaging, smoke-test the built wheel outside the checkout,
including the `nebula` command and bundled `py.typed` marker. CI runs these
checks on Python 3.11, 3.12, and 3.13.

Update the relevant docs and the README's **Known gaps** list when support
changes. See `docs/development/adding-sources.md` before adding an adapter.
