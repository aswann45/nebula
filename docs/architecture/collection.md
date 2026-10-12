# Collection infrastructure

`CollectionRunner` composes a discovery strategy, source fetch function,
parser, optional record filter, storage backend, and checkpoint store. It
uses a fixed number of workers instead of creating a task for every
discovered resource. Failures are collected per resource so successful
records remain available.

Discovery strategies cover explicit resource lists, an HTML index, and
cursor-based pages. Paginated discovery follows the source's explicit
continuation signal; an empty page alone does not signal completion.
The OMB service uses the HTML strategy. No Congress.gov paginated endpoint
is connected yet.

Checkpoints contain completed, filtered, and failed resource IDs plus a
configuration fingerprint. Filesystem storage writes each record atomically
and exports JSON or JSONL as a stream. The collection runner can omit
in-memory records with `retain_records=False`. See the
[collection guide](../user-guide/collection.md) for usage and limits.
