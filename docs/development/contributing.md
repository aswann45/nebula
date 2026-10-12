# Contributing

Use Python 3.11 or newer and Poetry 2.4 or newer. Install the locked
development and documentation dependencies:

```bash
poetry install --with dev,ruff,docs
```

Keep changes focused on a supported source operation. Preserve existing
public import paths and response-wrapper behavior where practical. Add a
typed method when changing an old method's return type would break callers.
Use NumPy-style docstrings for public APIs and keep Python lines within 79
characters. Never put source credentials or response bodies in errors.

Before submitting a change, run the checks in the
[testing guide](testing.md), update the source and user documentation, and
verify the built wheel if packaging changed.
