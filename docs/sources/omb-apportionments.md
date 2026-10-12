# OMB apportionments

`OMBApportionmentsClient` discovers JSON files from the OMB HTML index and
retrieves individual files. `list_apportionment_references()` returns
validated URL references; `get_apportionment_model(url)` returns a typed
record or `None` when that JSON file is absent.

```python
from nebula import Nebula

async with Nebula() as nebula:
    references = await nebula.apportionments.list()
    if references:
        record = await nebula.apportionments.get(references[0].url)
```

`collect_result(fiscal_year)` uses the shared runner and reports successes,
skips, and per-resource failures. With filesystem storage and a checkpoint,
the run can resume without redownloading completed files. The HTML parser
resolves relative URLs, deduplicates links, and restricts links to the OMB
host. The JSON parser works on local bytes without an HTTP connection.

Amounts are whole-number integers; fractional values fail validation.
Account identifiers remain strings, preserving leading zeroes. The typed
model uses `schedule_data`. The legacy wrapper still exposes its original
`schedue_data` key for compatibility. Fiscal-year filtering happens after
retrieval because the index does not currently provide a reliable year
filter.
