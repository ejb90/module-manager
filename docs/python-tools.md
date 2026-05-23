# Python Tools

Python CLIs are installed with `uv tool install`. Each deployed version gets
isolated `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` paths.

`uv` is an external runtime requirement for `--execute-install`. It is not a
Python package dependency because `module-manager` shells out to the `uv`
executable and is intended to be installable by `uv` itself.

## Deploy from PyPI

```sh
module-manager deploy-python ruff 0.8.0 \
  --package 'ruff==0.8.0' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

Without `--execute-install`, the command creates the versioned directories and
modulefile only. The module help includes the `uv tool install` command that an
administrator can run later.

Deployments also make the deployed version the module default, so `module load
ruff` resolves to `ruff/0.8.0`. Add `--no-default` to leave the current default
unchanged.

## Deploy from a Private Index

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --index https://packages.example/simple \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

`--index` may be used more than once.

## Deploy from a Wheelhouse

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --find-links /prod/wheels \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

`--find-links` may be used more than once.

## Deploy from VCS

`--package` is passed directly to `uv tool install`, so VCS package specs are
supported.

```sh
module-manager deploy-python mytool 1.0.0 \
  --package 'git+https://github.com/org/repo.git@v1.0.0' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

For a package in a repository subdirectory:

```sh
module-manager deploy-python mytool 1.0.0 \
  --package 'git+https://github.com/org/repo.git@v1.0.0#subdirectory=python/mytool' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

The positional `NAME` and `VERSION` values control the module path, for example
`module load mytool/1.0.0`; they are not inferred from the VCS URL.

## macOS Scratch Example

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --prefix /private/tmp/module-manager-tools \
  --module-root /private/tmp/module-manager-modulefiles \
  --execute-install
```
