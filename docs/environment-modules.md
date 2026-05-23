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
- includes `module-whatis`
- includes install guidance in `module help`

For `ruff/0.8.0`, the root variable is:

```sh
RUFF_ROOT=/prod/tools/ruff/0.8.0
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
