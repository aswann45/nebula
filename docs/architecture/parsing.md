# Parsing

Parsers receive source bytes and return validated Pydantic models. They do
not require an HTTP client, which allows local-file use and offline tests.

```python
from pathlib import Path
from nebula.omb_apportionments.parsers import OMBApportionmentParser

raw = Path("apportionment.json").read_bytes()
record = OMBApportionmentParser().parse(raw)
print(record.file_id)
```

Source-specific parsers live beside their source models. The OMB HTML
parser handles discovery separately from the JSON record parser. Parsing
errors and data validation errors are distinct from network errors.
Source wrappers retain legacy fields where return-type changes would break
existing callers.
