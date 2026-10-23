# Environment Modules

Generated modulefiles are Tcl modulefiles for Environment Modules.

Use a generated module tree:

```sh
module use /prod/modulefiles
module load ruff
ruff --version
```

You can also load an explicit version:

```sh
module load ruff/0.8.0
ruff --version
```

## Generated Modulefile Behavior

Each modulefile:

- prepends the tool's versioned `bin` directory to `PATH`
- sets `<TOOL>_ROOT`
- exports any variables supplied with `--env NAME=VALUE`
- includes `module-whatis`
- includes install guidance in `module help`

For `ruff/0.8.0`, the root variable is:

```sh
RUFF_ROOT=/prod/tools/ruff/0.8.0
```

Use `--env` more than once to export additional variables when the module is
loaded. Values are treated literally, so shell expansion is not performed by
the modulefile.

```sh
module-manager deploy-rust ripgrep 14.1.1 \
  --binary ./target/release/rg \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --env RIPGREP_CONFIG_PATH=/etc/rg.conf \
  --env RUST_BACKTRACE=1
```

## Default Versions

Deploy commands write a default-version selector by default:

```text
/prod/modulefiles/<name>/.version
```

For `ruff/0.8.0`, this makes `module load ruff` resolve to `ruff/0.8.0`.

Use `--no-default` when a deployment should not update the default version:

```sh
module-manager deploy-python ruff 0.8.0 \
  --package 'ruff==0.8.0' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --no-default
```

Uninstall removes the default selector only when it still points at the version
being removed. If another deployment has already made a newer version the
default, that selector is left alone.

Collective environments use the same modulefile behavior, but the versioned
`bin` directory contains every tool listed in the manifest.

Each completed deployment also writes
`<prefix>/<name>/<version>/module-manager.lock.json`. The lockfile records the
deployment metadata and SHA-256 checksums for the generated modulefile and
executables.

`verify` reports missing, modified, or unexpected executables in the managed
`bin` directory. For a Python deployment created without `--execute-install`,
run the displayed `uv tool install` command and then rerun `deploy-python` to
record its installed executables in the lockfile.

## Inspect Deployments

List recorded deployments, show their lockfile metadata, or verify that the
tracked files still match their recorded checksums:

```sh
module-manager list --prefix /prod/tools
module-manager show ruff 0.8.0 --prefix /prod/tools --module-root /prod/modulefiles
module-manager verify ruff 0.8.0 --prefix /prod/tools --module-root /prod/modulefiles
```

For collective environments, define variables in the manifest's
`[environment]` table, or add them on the command line with `--env`. Command
line values take precedence over a manifest variable with the same name.

```toml
[environment]
DEV_TOOLS_CACHE = "/scratch/dev-tools"
```
