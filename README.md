# module-manager

![tests](https://github.com/ejb90/module-manager/actions/workflows/test.yml/badge.svg)
[![Coverage](https://codecov.io/gh/ejb90/module-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/ejb90/module-manager)
[![License](https://img.shields.io/github/license/ejb90/module-manager)](LICENSE)
![Ruff](https://img.shields.io/badge/code%20style-ruff-261230)
[![Documentation](https://readthedocs.org/projects/module-manager/badge/?version=latest)](https://module-manager.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/env-module-manager)](https://pypi.org/project/env-module-manager/)
[![Python versions](https://img.shields.io/pypi/pyversions/env-module-manager)](https://pypi.org/project/env-module-manager/)

`module-manager` deploys versioned Python and Rust CLI tools behind GNU
environment modulefiles for Linux/HPC systems.

It writes tools and modulefiles into predictable versioned locations:

```text
/prod/tools/<name>/<version>/bin
/prod/modulefiles/<name>/<version>
```

## Quick Start

Deploy a Python CLI with `uv tool install`:

```sh
module-manager deploy-python ruff 0.8.0 \
  --package 'ruff==0.8.0' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

Deploy a Rust binary:

```sh
module-manager deploy-rust ripgrep 14.1.1 \
  --binary ./target/release/rg \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

Use the generated module:

```sh
module use /prod/modulefiles
module load ruff/0.8.0
ruff --version
```

## Documentation

Full documentation lives in `docs/` and can be served with MkDocs:

```sh
uv run mkdocs serve
```

Start with `docs/index.md` for installation, configuration, Python tools, Rust
tools, and local development notes.
