# Quickstart

The facade creates source clients as needed and closes owned HTTP pools on
exit. All retrieval operations are asynchronous.

```python
import asyncio
from nebula import Nebula


async def main() -> None:
    async with Nebula() as nebula:
        members = await nebula.members.list(chamber="house")
        print(len(members))
        references = await nebula.apportionments.list()
        if references:
            record = await nebula.apportionments.get(references[0].url)
            if record is not None:
                print(record.file_id, record.fiscal_year)


asyncio.run(main())
```

The same operations are available from the command line:

```bash
nebula members list --chamber house --format json
nebula apportionments list --format table
```

See the [Python API](../user-guide/python-api.md) and
[CLI guide](../user-guide/cli.md) for the supported operations.
