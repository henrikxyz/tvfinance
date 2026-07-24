# Contributing

Create focused changes that leave the repository working at every commit.

1. Install Python 3.10 or newer and `uv`.
2. Run `uv sync --all-groups`.
3. Add tests before or with behavior changes.
4. Run every quality gate locally.
5. Keep commit messages concise and describe one completed change.

Do not commit generated distributions, local databases, virtual environments,
credentials, captured private data, or editor configuration.

## Compiled requirements

`pyproject.toml` is the dependency source of truth. Regenerate the install lists
after changing dependencies:

```bash
uv pip compile pyproject.toml --universal -o requirements.txt
uv pip compile pyproject.toml --extra mcp --universal -o requirements-mcp.txt
uv pip compile pyproject.toml --group dev --universal -o requirements-dev.txt
uv pip compile pyproject.toml --group docs --universal -o requirements-docs.txt
```

Commit all affected requirement files together with the source dependency
change. `requirements-mcp.txt` is also the requirements file used for hosted
MCP deployments.
