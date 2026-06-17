# Python Tools

Python CLIs are installed with `uv tool install`. Each deployed version gets
isolated `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` paths.

The install subprocess ignores inherited `UV_TOOL_*` settings so the managed
destination and install behavior are not changed by the invoking environment.
Other uv settings, including `UV_CONFIG_FILE`, are preserved.

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
  --default-index https://packages.example/simple \
  --index https://packages.example/simple \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

`--index` may be used more than once. Use `--default-index` to replace uv's
default package index, or `--no-index` when resolution should use only direct
URLs and `--find-links` locations.

## Deploy from a Wheelhouse

Use `--find-links` when wheels are staged in a directory or simple HTML page:

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --find-links /prod/wheels \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

Add `--no-index` to make the install fully wheelhouse-only:

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --find-links /prod/wheels \
  --no-index \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

`--find-links` may be used more than once.

## Deploy from a Wheel URL

Pass a direct wheel URL or file URL as the package spec:

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package 'gitconductor @ https://packages.example/files/gitconductor-0.1.0-py3-none-any.whl' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

For a local wheel file:

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package 'gitconductor @ file:///prod/wheels/gitconductor-0.1.0-py3-none-any.whl' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

## Use Constraint Files

Pass requirement constraint files to `uv tool install`:

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --constraints /prod/constraints/runtime.txt \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

`--constraints` may be used more than once.

## Cache and Refresh Controls

Pass uv cache controls through when you need fresh index or package metadata:

```sh
module-manager deploy-python gitconductor 0.1.0 \
  --package gitconductor==0.1.0 \
  --refresh \
  --refresh-package gitconductor \
  --no-cache \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

Use `--force` or `--reinstall` when re-running an install into an existing
versioned tool environment.

## Generate Constraint Files

Use `auto-constraints` to compile a package and its dependencies into a
constraints file:

```sh
module-manager auto-constraints gitconductor==0.7.0 \
  --index https://packages.example/simple \
  --output constraints.txt
```

The command runs `uv pip compile` and writes `constraints.txt` by default. If uv
reports a transitive URL dependency, `module-manager` adds the suggested
`name @ URL` requirement and retries until all URL dependencies have been
included or uv reports an unrecoverable error.

## Use a uv Config File

Pass a specific uv configuration file to `uv tool install`:

```sh
module-manager deploy-python internal-tool 1.2.3 \
  --package internal-tool==1.2.3 \
  --uv-config-file /prod/config/uv.toml \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

The same option can be set in the module-manager config file:

```toml
[python]
uv_config_file = "/prod/config/uv.toml"
```

Use uv's own `UV_CONFIG_FILE` environment variable if you want to configure uv
through the environment.

## Deploy from VCS

`--package` is passed directly to `uv tool install`, so Git package specs are
supported. Pin a tag, branch, or commit to keep deployments reproducible.

```sh
module-manager deploy-python mytool 1.0.0 \
  --package 'git+https://github.com/org/repo.git@v1.0.0' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install
```

For an SSH Git URL:

```sh
module-manager deploy-python mytool 1.0.0 \
  --package 'git+ssh://git@github.com/org/repo.git@v1.0.0' \
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
