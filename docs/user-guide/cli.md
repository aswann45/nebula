# Command-line interface

The CLI delegates to the same domain services as the Python API.

| Command | Supported operation |
| --- | --- |
| `sources list`, `sources status [--check]` | Capabilities and optional live check |
| `config show`, `config validate` | Masked settings and validation |
| `members get ID`, `members list [--chamber house|senate]` | Congress.gov lookup or current GitHub members |
| `members historical --year YEAR` | Historical GitHub members |
| `members house-current`, `members senate-current` | Clerk rosters |
| `committees list`, `committees current` | Current GitHub committees |
| `votes house --year YEAR [--roll-call N]` | House roll calls |
| `votes collect-house --year YEAR` | Resumable House year collection |
| `apportionments list`, `apportionments get URL` | OMB discovery and retrieval |
| `apportionments collect [--fiscal-year YEAR]` | OMB bulk collection |

Retrieval commands accept `--format table|json|jsonl|csv`, `--output`,
`--overwrite`, `--quiet`, and `--verbose`. JSON and JSONL are suitable for
automation. Nested CSV values are encoded as compact JSON in a cell.
Progress and diagnostics go to stderr, leaving structured stdout clean.

For persistent House or OMB collection, use JSON or JSONL with `--output`.
`--resume` retries failures using a checkpoint; `--preserve-raw` stores
source bytes; `--checkpoint PATH` selects a checkpoint file.

| Exit code | Meaning |
| --- | --- |
| 0 | Success |
| 2 | Invalid arguments |
| 3 | Configuration error |
| 4 | Network or missing-resource error |
| 5 | Parsing or validation error |
| 6 | Partial collection |
| 7 | Output or storage error |

There are no legislation commands yet because the underlying bill and
amendment retrieval operations remain unimplemented.
