# Source adapters

`SourceRegistry` explicitly registers each source client with a stable name
and `SourceCapabilities`. The built-in names are `congress_gov`,
`house_clerk`, `senate_clerk`, `github_congress`, and
`omb_apportionments`. Capabilities tell callers which domains and bulk
methods are currently available; they are declarations, not live checks.

Sources keep their own request construction and authentication. Congress.gov
uses JSON and an API key, the clerks publish XML, GitHub publishes YAML,
and OMB lists JSON files in HTML. A source may expose typed methods while
retaining older response-wrapper methods for compatibility.

The registry is explicit. Dynamic plugin discovery is not implemented.
See [adding sources](../development/adding-sources.md) for the extension
steps.
