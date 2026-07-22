# Testing

The default suite is offline and deterministic.

- **Unit tests** validate models, validation, policies, and pure parsers.
- **Contract tests** replay sanitized HTTP and WebSocket payloads.
- **Integration tests** connect components through in-memory transports.
- **Live tests** verify external protocol compatibility and require explicit
  opt-in.

Fixtures must be minimal, sanitized, and free of cookies, account identifiers,
authorization headers, and unrelated payload fields.
