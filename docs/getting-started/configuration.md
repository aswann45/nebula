# Configuration

Only Congress.gov member lookup currently needs a credential. Set
`CONGRESS_GOV_API_KEY` in the environment or in a `.env` file in the current
working directory. Environment variables take precedence over `.env` values.
The repository's `.env.example` gives the expected key name. Keep real keys
out of version control.

```bash
export CONGRESS_GOV_API_KEY=your-key
nebula config validate
nebula sources status
```

`nebula config show` masks the key. `sources status` reports local
configuration; add `--check` to make live source requests. Credentials are
read through `nebula.settings.Settings`, a Pydantic Settings class. The
Congress.gov client also accepts an explicit `API_KEY` for programmatic use.

`HTTPConfig(timeout=30, max_connections=20, max_concurrency=5,
max_retries=3, backoff_factor=0.5)` validates transport limits. Pass it to
`Nebula(config=...)` or a direct source client. Retries apply to transient
idempotent requests, including rate limits and selected server errors.
