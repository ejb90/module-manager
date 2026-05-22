# Contributing

Contributions are welcome. This project uses `uv` for local development,
Ruff for linting/formatting, Pytest for tests, and MkDocs for documentation.

## Setup

```sh
uv sync --group dev
```

## Checks

Run the same core checks used by CI:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
uv run mkdocs build --strict
```

Format code before opening a pull request:

```sh
uv run ruff format .
```

## Documentation

Preview documentation locally:

```sh
uv run mkdocs serve
```

Then open:

```text
http://127.0.0.1:8000
```

## Releases

Release tags use the project version from `pyproject.toml`:

```sh
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions handles release publishing for matching `v*` tags.
