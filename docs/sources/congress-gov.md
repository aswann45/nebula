# Congress.gov

`CongressGovClient` retrieves member records by Bioguide ID. Its typed
`get_member_model(id)` method returns a validated `Member`; the existing
`get_member_data(ids)` method retains its public mapping contract and bounds
parallel requests. `Nebula.members.get` and `get_many` use these methods.

Set `CONGRESS_GOV_API_KEY` in the environment or `.env`. The key is loaded
on demand and omitted from error messages and displayed configuration.

```python
from nebula import Nebula

async with Nebula() as nebula:
    member = await nebula.members.get("B000490")
```

Bill and amendment methods currently raise `NotImplementedError`; no
legislation service or CLI retrieval command is exposed. A paginated
Congress.gov collection adapter has not yet been connected to the shared
runner.
