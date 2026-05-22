# module-manager

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
