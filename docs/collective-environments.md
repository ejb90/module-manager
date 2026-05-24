# Collective Environments

Collective environments package several tools behind one modulefile. Use them
when a shared workflow needs Python CLIs, Rust binaries, and shell scripts to
appear together from one `module load`.

Create a TOML manifest:

```toml
name = "dev-tools"
version = "2026.05"
description = "Shared developer command-line tools"
prefix = "/prod/tools"
module_root = "/prod/modulefiles"
default = true

[[tools]]
type = "python"
name = "ruff"
version = "0.8.0"
package = "ruff==0.8.0"
python = "3.12"
indexes = ["https://packages.example/simple"]
find_links = ["/prod/wheels"]
uv_config_file = "/prod/config/uv.toml"

[[tools]]
type = "rust"
name = "ripgrep"
version = "14.1.1"
binary = "./target/release/rg"

[[tools]]
type = "script"
name = "lab-helper"
version = "1.0.0"
script = "./scripts/lab-helper"
```

Deploy the environment:

```sh
module-manager deploy-env --file dev-tools.toml
```

This writes one shared environment:

```text
/prod/tools/dev-tools/2026.05/bin
/prod/modulefiles/dev-tools/2026.05
```

The generated modulefile prepends the shared `bin` directory to `PATH`, so all
tools in the manifest are available after:

```sh
module use /prod/modulefiles
module load dev-tools
```

Relative `binary` and `script` paths are resolved relative to the manifest file.

## Preview

Use `--dry-run` to preview the install, copy, and modulefile actions without
creating files:

```sh
module-manager deploy-env --file dev-tools.toml --dry-run
```

## Overrides

The manifest can define `prefix`, `module_root`, and `default`, but CLI options
can override them:

```sh
module-manager deploy-env \
  --file dev-tools.toml \
  --prefix /scratch/tools \
  --module-root /scratch/modulefiles \
  --no-default
```
