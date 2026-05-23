# Agents

This file gives coding agents the local rules for working in this repository.

## Project Shape

`module-manager` is a Python CLI for deploying versioned command-line tools
behind GNU Environment Modules on Linux/HPC systems. The published package name
is `env-module-manager`, the import package is `module_manager`, and the console
script is `module-manager`.

The core package lives in `module_manager/`, tests live in `tests/`, and MkDocs
documentation lives in `docs/`.

Important modules:

* `module_manager/cli.py`: Rich Click command group and CLI wrappers.
* `module_manager/config.py`: TOML and environment configuration loading.
* `module_manager/deploy.py`: filesystem deployment and uninstall behavior.
* `module_manager/modulefile.py`: Tcl modulefile and default-version rendering.
* `tests/test_cli.py`: command-line behavior tests.
* `tests/test_config.py`: configuration precedence tests.
* `tests/test_modulefile.py`: modulefile and deployment helper tests.

## Commands

Use these commands when validating changes:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
uv run mkdocs build --strict
uv build
uv run twine check dist/*
```

The test suite is configured with coverage and a 90 percent fail-under
threshold, so targeted pytest runs can fail coverage even when the selected test
passes. Run the full suite before treating coverage as meaningful.

## Coding Rules

* Preserve user changes. Do not revert unrelated dirty work.
* Use typed function signatures throughout tests and source code.
* Use Google-style docstrings for new or edited functions.
* Keep Click command functions thin; put filesystem behavior in
  `module_manager.deploy`.
* Keep modulefile string generation in `module_manager.modulefile`.
* Prefer `pathlib.Path` over string path manipulation.
* Prefer structured subprocess calls such as `subprocess.run([...], check=True)`.
* Keep edits scoped. Avoid opportunistic refactors while fixing a bug.
* Update docs and `README.md` when changing user-facing CLI behavior.

## CLI Behavior

Deploy commands create versioned install roots under `<prefix>/<name>/<version>`
and modulefiles under `<module-root>/<name>/<version>`.

Supported deploy commands:

* `deploy-python`: writes a modulefile for a Python CLI, and can install it with
  `uv tool install`.
* `deploy-rust`: copies a compiled binary into the versioned `bin` directory.
* `deploy-script`: copies a shell script into the versioned `bin` directory.

Deployments write `<module-root>/<name>/.version` by default so `module load
<name>` resolves to the deployed version. Use `--no-default` to skip that.

`uninstall` removes one versioned install root and modulefile. It removes the
default selector only when it still points at the version being removed. Use
`--dry-run` to show paths without deleting them, and `--keep-default` to leave
the default selector untouched.

## Configuration

Configuration can come from `~/.config/module-manager/config.toml`, a path set
with `MODULE_MANAGER_CONFIG`, environment variables, or CLI options. CLI options
take precedence over environment values, which take precedence over TOML.

Common settings:

* `prefix` or `MODULE_MANAGER_PREFIX`
* `module_root` or `MODULE_MANAGER_MODULE_ROOT`
* `[python].indexes`, `MODULE_MANAGER_INDEX`, or `MODULE_MANAGER_INDEXES`
* `[python].find_links` or `MODULE_MANAGER_FIND_LINKS`

## Documentation

MkDocs Material is used for documentation. Update `mkdocs.yml` navigation when
adding pages. The Material theme currently prints an upstream warning during
`mkdocs build --strict`; the build is still valid when the command exits zero.
