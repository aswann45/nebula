# Senate Clerk

`SenateClerkClient` retrieves the current Senate member roster as XML.
`get_current_member_model()` returns a validated source record and
`Nebula.members.senate_current()` exposes it through the facade.

```python
from nebula import Nebula

async with Nebula() as nebula:
    roster = await nebula.members.senate_current()
```

The older response-wrapper method remains available. Senate roll-call
retrieval and committee assignment collection are not currently supported.
