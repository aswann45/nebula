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

`nebula.votes.house_year(year)` checks roll numbers through the Clerk's
listed maximum, skips missing XML files, and bounds concurrent requests.
It does not yet create checkpoints or incremental record files. The
House roll-call parser also accepts local XML bytes.
