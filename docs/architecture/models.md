# Models and data fidelity

Public records and configuration use Pydantic v2. Source models reflect the
published source structure. Domain models normalize shared concepts such
as members, committees, and votes where evidence supports a common field.
Keep the source model when its extra fields matter.

Public models support `model_dump()`, `model_dump(mode="json")`, and
`model_dump_json()` without network access or parsing side effects. Dates
and timestamps use Python date types. OMB approved amounts use integers
because published amounts are whole numbers; account codes stay text so
leading zeroes are retained.

House batch requests and flattened GitHub member records use Pydantic
validation. The legacy `nebula.typings` names remain importable for existing
callers. Legacy response wrappers still return their documented dictionaries;
House vote and flattened GitHub member data are validated before return.

Collection provenance is stored separately from source record data.
Retrieval time and source-supplied modification time have different meanings
and are not substituted for one another.
