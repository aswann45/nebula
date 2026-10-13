# Python API

`Nebula` exposes `members`, `committees`, `votes`, `apportionments`, and
`legislation` services. Services return validated source models for their
supported operations.

```python
from nebula import Nebula

async with Nebula() as nebula:
    member = await nebula.members.get("B000490")
    committees = await nebula.committees.current()
    vote = await nebula.votes.house(2026, 125)
    house_votes = await nebula.votes.house_year_result(2026)
    actions = await nebula.legislation.bill_actions(117, "hr", 3076)
    bills = await nebula.legislation.collect_bills_result(119, "hr")
    collected = await nebula.apportionments.collect_result(2026)
    print(house_votes.summary())
    print(actions.actions, actions.pagination.next)
    print(bills.summary())
    print(collected.summary())
```

`members.get` requires a Congress.gov key. `votes.house` returns `None`
for an absent roll call; `apportionments.get` returns `None` for an absent
JSON file. Collection results keep successful records and report per-resource
failures. Use `votes.house_year_result()` or
`apportionments.collect_result()` when the failure summary matters.

For direct source access, import a client from its existing package path:

```python
from nebula.omb_apportionments.client import OMBApportionmentsClient

async with OMBApportionmentsClient() as client:
    references = await client.list_apportionment_references()
```

Older response-wrapper methods remain available. Prefer typed methods such
as `get_apportionment_model()`, `get_roll_call_vote_model()`, and
`get_current_members()` for new code.
