# module-manager

![tests](https://github.com/ejb90/module-manager/actions/workflows/test.yml/badge.svg)
[![Coverage](https://codecov.io/gh/ejb90/module-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/ejb90/module-manager)
[![License](https://img.shields.io/github/license/ejb90/module-manager)](LICENSE.md)
![Ruff](https://img.shields.io/badge/code%20style-ruff-261230)
[![Documentation](https://readthedocs.org/projects/module-manager/badge/?version=latest)](https://module-manager.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/env-module-manager)](https://pypi.org/project/env-module-manager/)
[![Python versions](https://img.shields.io/pypi/pyversions/env-module-manager)](https://pypi.org/project/env-module-manager/)

`module-manager` deploys versioned Python, Rust, shell, and collective CLI
environments behind GNU environment modulefiles for Linux/HPC systems.

It writes tools and modulefiles into predictable versioned locations:

```text
/prod/tools/<name>/<version>/bin
/prod/modulefiles/<name>/<version>
```

The installation prefix and module root must be different directories.

## Installation

Install from PyPI:

```sh
pip install env-module-manager
```

Or install as a uv-managed tool:

```sh
uv tool install env-module-manager
```

## Quick Start

Deploy a Python CLI with `uv tool install`:

```sh
module-manager deploy-python ruff 0.8.0 \
  --package 'ruff==0.8.0' \
  --default-index https://packages.example/simple \
  --constraints /prod/constraints/runtime.txt \
  --uv-executable /opt/uv/bin/uv \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

Set `MODULE_MANAGER_UV_EXECUTABLE=/opt/uv/bin/uv` to use the same uv path by
default.

To expose executable entry points from direct dependencies too, add
`--with-executables-from=package1,package2`. Used without package names, the
option reads `[project].dependencies` from the current directory's
`pyproject.toml`.

Python deployments also pass through uv's `--with`, `--with-requirements`,
`--constraints`, `--overrides`, `--lfs`, `--verbose`, `--native-tls`, and
`--no-config` options. `--config-file` is accepted as an alias for
`--uv-config-file`.

Deploy a Rust binary:

```sh
module-manager deploy-rust ripgrep 14.1.1 \
  --binary ./target/release/rg \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

Add `--env NAME=VALUE` to any deploy command to export a variable from the
generated modulefile. For `deploy-env`, variables can also be declared in the
manifest's `[environment]` table.

Generate a constraints file for a Python CLI:

```sh
module-manager auto-constraints ruff==0.8.0 --output constraints.txt
```

Deploy from a direct wheel or Git URL:

```sh
module-manager deploy-python my-tool 1.0.0 \
  --package 'my-tool @ file:///prod/wheels/my_tool-1.0.0-py3-none-any.whl' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

Deploy a shell script:

```sh
module-manager deploy-script my-tool 1.0.0 \
  --script ./scripts/my-tool \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

Deploy a collective environment from a TOML manifest:

```sh
module-manager deploy-env --file dev-tools.toml --dry-run
module-manager deploy-env --file dev-tools.toml
```

Use the generated module:

```sh
module use /prod/modulefiles
module load ruff
ruff --version
```

Deployments make the deployed version the module default. Add `--no-default`
when you want to write the versioned modulefile without changing the default.

Remove a deployed version:

```sh
module-manager uninstall ruff 0.8.0 \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

## Documentation

Read the full documentation on
[Read the Docs](https://module-manager.readthedocs.io/).
