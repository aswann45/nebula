# Collection and resume

House votes and OMB apportionments use the shared collection runner.
The House service discovers roll IDs from the Clerk's paginated listing;
OMB discovers JSON links from its HTML index. Both download with bounded
workers, validate records, and report partial failures.

```bash
nebula apportionments collect --fiscal-year 2026 --output ./data/omb/
nebula apportionments collect --fiscal-year 2026 --output ./data/omb/ --resume
nebula votes collect-house --year 2026 --output ./data/house/ --resume
```

JSON or JSONL output creates a companion directory containing one validated
record file per resource, a checkpoint, and collection metadata. Add
`--preserve-raw` to retain source bytes. Exported records have `record` and
`provenance` keys; provenance includes source URL, retrieval time, parser
version, record ID, and raw-content SHA-256. A source publication time is
recorded only when the source supplies it.

Use the Python API to manage storage explicitly:

```python
from nebula import Nebula
from nebula.collection.checkpoints import FileCheckpointStore
from nebula.storage import FilesystemStorage

storage = FilesystemStorage("data/omb")
checkpoint = FileCheckpointStore("data/omb/checkpoint.json")
async with Nebula() as nebula:
    result = await nebula.apportionments.collect_result(
        2026,
        storage=storage,
        checkpoint_store=checkpoint,
        resume=True,
        retain_records=False,
    )
print(result.summary())
```

Checkpoint fingerprints detect changes to the source, filter, parser
version, and raw-preservation setting. Completed resources are skipped on
resume when their stored record validates; failed resources are retried.
Cancellation preserves completed record files and checkpoint progress.
`retain_records=False` avoids keeping all parsed models in memory.

The fiscal-year filter currently runs after retrieval, so all indexed OMB
JSON files are downloaded.
