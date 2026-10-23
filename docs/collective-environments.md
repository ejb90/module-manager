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

[environment]
DEV_TOOLS_CACHE = "/scratch/dev-tools"

[[tools]]
type = "python"
name = "ruff"
version = "0.8.0"
package = "ruff==0.8.0"
with = ["ruff-lsp==0.1"]
with_requirements = ["requirements.txt"]
editable = false
with_editable = ["/src/ruff-plugin"]
with_executables_from = ["ruff-lsp", "ruff-format"]
python = "3.12"
indexes = ["https://packages.example/simple"]
default_index = "https://packages.example/simple"
find_links = ["/prod/wheels"]
no_index = false
index_strategy = "first-index"
constraints = ["/prod/constraints/runtime.txt"]
overrides = ["/prod/overrides.txt"]
no_cache = false
refresh = false
refresh_packages = ["ruff"]
force = false
reinstall = false
lfs = false
verbose = 0
native_tls = false
no_config = false
uv_config_file = "/prod/config/uv.toml"
uv_executable = "/opt/uv/bin/uv"

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

Use `--uv-executable` when all Python tools in the manifest should use a
specific uv executable:

```sh
module-manager deploy-env --file dev-tools.toml --uv-executable /opt/uv/bin/uv
```

You can also set the same default with `MODULE_MANAGER_UV_EXECUTABLE`, or set
`uv_executable` on an individual Python tool in the manifest when only that
entry needs a different executable.

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

The top-level `[environment]` table exports literal environment variables when
the collective module loads. You can add or override values at deployment time
with repeatable `--env NAME=VALUE` options; command-line values take precedence
over variables in the manifest.

```sh
module-manager deploy-env --file dev-tools.toml --env RUST_BACKTRACE=1
```

Relative `binary` and `script` paths are resolved relative to the manifest file.
Relative Python `constraints` paths are resolved the same way.

For a Python tool, set `with_executables_from` to expose executable entry
points from its dependencies as well. It is a list of package names and maps to
uv's `--with-executables-from=package1,package2` option.

Set `editable = true` to install the Python tool's package in editable mode.
Use `with_editable = ["/path/to/package"]` to add extra editable packages.
Use `with = ["package==1"]`, `with_requirements = ["requirements.txt"]`,
`overrides = ["overrides.txt"]`, and `lfs = true` for the corresponding uv
options. Relative requirement and override file paths are resolved relative to
the manifest.

Set `verbose` to an integer for repeated `-v` flags. `native_tls = true` and
`no_config = true` pass through their corresponding uv runtime controls; use
the existing `uv_config_file` key for an explicit uv configuration file.

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
