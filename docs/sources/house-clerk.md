# House Clerk

`HouseClerkClient` retrieves the current House roster and House roll-call
XML. `get_current_member_model()` and `get_roll_call_vote_model(year, roll)`
provide typed records. The vote method returns `None` for a missing roll.

```python
from nebula import Nebula

async with Nebula() as nebula:
    roster = await nebula.members.house_current()
    vote = await nebula.votes.house(2026, 125)
```

`nebula.votes.house_year(year)` follows the Clerk's paginated vote listing
for that year, requests only listed roll numbers, skips missing XML files,
and bounds concurrent requests. The archive's `index.asp` page is not
available. Listing discovery supports voting years from 1935 onward.
`house_year_result()` also accepts storage and checkpoint options for
resumable collection and reports failed roll files. The House roll-call
parser accepts local XML bytes.
