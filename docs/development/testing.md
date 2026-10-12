# Testing and release checks

Ordinary tests use local XML, JSON, and YAML fixtures with mocked HTTP.
They do not require live source access or credentials. Run the same gates
as CI:

```bash
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src
poetry run pytest -q
poetry run mkdocs build --strict
poetry build
```

CI tests Python 3.11, 3.12, and 3.13. It installs the wheel in a fresh
virtual environment, imports `nebula` outside the checkout, checks that
`py.typed` is present, and runs `nebula --help`. A separate integration test
may use live sources, but it must be opt-in and marked clearly.

Test files are grouped by the component or source under test, such as
`tests/core`, `tests/services`, `tests/collection`, and `tests/cli`.
When changing externally visible behavior, add a regression test using
representative source content.
