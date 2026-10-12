# GitHub congressional legislators

`GitHubCongressClient` reads published YAML files for current and historical
legislators and current committees. The typed methods are
`get_current_members()`, `get_historical_members(year)`, and
`get_current_committees()`.

```python
from nebula import Nebula

async with Nebula() as nebula:
    members = await nebula.members.historical(2020)
    committees = await nebula.committees.current()
```

`members.list(chamber="house")` filters the current GitHub member data by
the latest term. Source YAML fields remain in the validated source models.
The older response-wrapper client methods remain callable.
