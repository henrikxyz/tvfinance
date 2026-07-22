# Architecture overview

The project separates transport mechanics, domain behavior, and public
interfaces.

```text
Public Python API / CLI / MCP
             |
       Domain services
             |
   HTTP and WebSocket ports
             |
     Provider adapters
```

Domain services own validation, normalization, and result construction. They do
not know whether they were called from a synchronous API, asynchronous API, CLI,
or MCP tool.

Transport interfaces are injectable. Unit and contract tests use deterministic
in-memory transports; live endpoints are only exercised by an explicitly
enabled test suite.

## Dependency direction

- Public interfaces depend on domain services.
- Domain services depend on typed transport protocols and models.
- Provider adapters implement the transport protocols.
- Core modules never import CLI or MCP packages.
- Optional dependencies are imported lazily at their interface boundary.
