# Adding a source

1. Identify the source format, discovery mechanism, authentication, and
   stable resource IDs using representative published records.
2. Add a source-specific client that uses the shared `BaseClient` transport
   lifecycle. Keep request construction inside the client.
3. Add an independent parser and faithful Pydantic source models. Keep
   fields that are unique to the source.
4. Register the client explicitly in `SourceRegistry` with only the
   capabilities it actually supports.
5. Add a domain service operation where the data fits an existing domain.
   Wire a collection through `CollectionRunner` only when bulk retrieval is
   supported.
6. Add offline fixtures and tests for parsing, missing resources, retries,
   and any collection resume behavior. Document authentication, fields,
   errors, and public methods.

HTML indexes, XML files, YAML datasets, and JSON APIs can use different
discovery functions. Do not force a source into REST pagination or a
canonical congressional model if its published data does not fit.
