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

For collective environments, define variables in the manifest's
`[environment]` table, or add them on the command line with `--env`. Command
line values take precedence over a manifest variable with the same name.

```toml
[environment]
DEV_TOOLS_CACHE = "/scratch/dev-tools"
```
