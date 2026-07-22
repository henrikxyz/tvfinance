# Quality gates

Every commit must be independently installable and pass the same local checks
used by continuous integration:

```bash
uv run ruff format .
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest -q
uv lock --check
uv build
uv run --group docs mkdocs build --strict
```

Tests enforce 100% statement and branch coverage while the implementation is
developed. Any intentional exclusion must be documented next to the excluded
branch and reviewed before release.
