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
default_index = "https://packages.example/simple"
find_links = ["/prod/wheels"]
no_index = false
index_strategy = "first-index"
constraints = ["/prod/constraints/runtime.txt"]
no_cache = false
refresh = false
refresh_packages = ["ruff"]
force = false
reinstall = false
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
Relative Python `constraints` paths are resolved the same way.

## Multiple Python Tools

A collective environment can install several Python CLIs into the same shared
`bin` directory. Each Python tool can use its own package spec and uv resolver
options:

```toml
name = "python-dev-tools"
version = "2026.05"
prefix = "/prod/tools"
module_root = "/prod/modulefiles"

[[tools]]
type = "python"
name = "ruff"
version = "0.8.0"
package = "ruff==0.8.0"
python = "3.12"
constraints = ["constraints.txt"]

[[tools]]
type = "python"
name = "gitconductor"
version = "0.7.0"
package = "gitconductor==0.7.0"
default_index = "https://packages.example/simple"
constraints = ["constraints.txt"]
refresh_packages = ["gitconductor"]

[[tools]]
type = "python"
name = "internal-review"
version = "1.4.2"
package = "internal-review @ file:///prod/wheels/internal_review-1.4.2-py3-none-any.whl"
find_links = ["/prod/wheels"]
no_index = true
```

Deploy it with:

```sh
module-manager deploy-env --file python-dev-tools.toml
```

After `module load python-dev-tools`, the `ruff`, `gitconductor`, and
`internal-review` executables are available from one module.

## Python Tools and Bash Scripts

Use script entries for Bash helpers that should live alongside Python CLIs:

```toml
name = "release-tools"
version = "2026.05"
description = "Release automation helpers"
prefix = "/prod/tools"
module_root = "/prod/modulefiles"

[[tools]]
type = "python"
name = "gitconductor"
version = "0.7.0"
package = "gitconductor==0.7.0"
constraints = ["constraints.txt"]

[[tools]]
type = "python"
name = "changelog-builder"
version = "2.1.0"
package = "changelog-builder @ git+https://github.com/org/changelog-builder.git@v2.1.0"

[[tools]]
type = "script"
name = "release-check"
version = "1.0.0"
script = "./scripts/release-check.sh"

[[tools]]
type = "script"
name = "publish-docs"
version = "1.0.0"
script = "./scripts/publish-docs.sh"
```

Deploy it with:

```sh
module-manager deploy-env --file release-tools.toml
```

The script files are copied into the shared environment `bin` directory and
marked executable, so they appear on `PATH` next to the Python entry points.

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
