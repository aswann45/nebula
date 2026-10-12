# Installation

Nebula requires Python 3.11 or newer.

```bash
python -m pip install nebula
nebula --help
```

For a repository checkout, Poetry installs the package and development
tools from the lock file:

```bash
poetry install --with dev,ruff,docs
poetry run nebula --help
```

The wheel includes `py.typed` for type checkers. The `nebula` console script
is installed by the wheel, alongside the Python package. See
[configuration](configuration.md) before using Congress.gov endpoints.
