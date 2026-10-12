# Nebula

Nebula retrieves and validates legislative and government records from five
published sources. Use the asynchronous Python API for applications, the
direct clients for source-specific access, or the `nebula` command for
inspection and exports.

Start with [installation](getting-started/installation.md) and the
[quickstart](getting-started/quickstart.md). The [source pages](sources/congress-gov.md)
describe what each adapter currently supports. [Known gaps](https://github.com/aswann45/nebula#known-gaps)
are listed in the repository README.

```python
from nebula import Nebula

async with Nebula() as nebula:
    members = await nebula.members.list(chamber="senate")
    references = await nebula.apportionments.list()
```

Methods that contact a source require network access. The ordinary test
suite uses local fixtures and mocked HTTP responses.
