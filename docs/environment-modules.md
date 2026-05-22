# Environment Modules

Generated modulefiles are Tcl modulefiles for Environment Modules.

Use a generated module tree:

```sh
module use /prod/modulefiles
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
