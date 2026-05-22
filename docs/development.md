# Local Development

Run the CLI from the checkout:

```sh
uv run module-manager --help
```

Run checks:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Build distributions:

```sh
uv build
```

## macOS `.venv` Notes

On some macOS systems, a `.venv` tree can acquire the filesystem `hidden` flag.
Python 3.14 skips hidden `.pth` files, which can break editable installs.

One robust local workaround is to keep the real environment in `venv/` and point
`.venv` at it:

```sh
UV_PROJECT_ENVIRONMENT=venv uv sync
ln -s venv .venv
```

The project ignores both `.venv` and `venv/`.
