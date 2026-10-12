# Exceptions

`NebulaError` is the common base. Request errors include sanitized source
and request context; query values and credentials are excluded from error
messages.

| Error | Meaning |
| --- | --- |
| `ConfigurationError` | Invalid configuration or incompatible checkpoint |
| `AuthenticationError` | Credentials rejected |
| `RateLimitError` | Source rate limit |
| `ResourceNotFoundError` | Requested resource absent |
| `SourceUnavailableError` | Transient source or network failure |
| `ParsingError` | Source syntax or structure cannot be parsed |
| `DataValidationError` | Parsed content fails a data contract |
| `StorageError` | Record, checkpoint, or export I/O failure |

::: nebula.core.exceptions.NebulaError

::: nebula.core.exceptions.RequestError
