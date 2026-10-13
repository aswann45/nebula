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

`CongressGovClient` also retrieves one page of bill actions, bill
amendments, or amendment actions through typed methods. The corresponding
`Nebula.legislation` methods return typed records and pagination metadata.
Use `offset` and `limit` to request further pages; `limit` is at most 250.
`get_bill_page()` and `get_bill_model()` provide typed bill list and detail
records. `Nebula.legislation.collect_bills_result(congress, bill_type)`
follows the API's explicit next-page URL, then retrieves and validates each
bill detail through the shared bounded runner. Stable bill identities use
Congress, type, and number, so a changed list order does not invalidate
checkpoints. Collection supports storage, resume, and raw response retention.
