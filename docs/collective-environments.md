# Collective Environments

Collective environments package several tools behind one modulefile. Use them
when a shared workflow needs Python CLIs, binaries, and shell scripts to
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

[alias]
lint = "ruff check ."
format = "ruff format ."

[[tools]]
type = "python"
name = "ruff"
version = "0.8.0"
package = "ruff==0.8.0"
expose_python = "dev-python"
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
uv_force = false
reinstall = false
lfs = false
verbose = 0
native_tls = false
no_config = false
uv_config_file = "/prod/config/uv.toml"
uv_executable = "/opt/uv/bin/uv"

[[tools]]
type = "binary"
name = "ripgrep"
version = "14.1.1"
binary = "./target/release/rg"
binary_mode = "copy"

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

Use top-level `--force` only to replace an existing collective deployment. For
an individual Python tool, set `uv_force = true` to pass `--force` to
`uv tool install`.

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

The top-level `[environment]` table exports environment variables when the
collective module loads. `$NAME` and `${NAME}` references in its values are
expanded from the environment running `module-manager` before the modulefile is
written. You can add or override values at deployment time with repeatable
`--env NAME=VALUE` options; command-line values take precedence over variables
in the manifest and remain literal.

```toml
[environment]
DEV_TOOLS_CACHE = "$SCRATCH/dev-tools"
```

```sh
module-manager deploy-env --file dev-tools.toml --env PAGER=less
```

The top-level `[alias]` table defines shell aliases when the collective module
loads. Alias commands are written literally, so shell variables and other shell
expressions are evaluated when the alias is invoked.

```toml
[alias]
lint = "ruff check ."
show-cache = "echo $DEV_TOOLS_CACHE"
```

Relative `binary` and `script` paths are resolved relative to the manifest file.
Relative Python `constraints` paths are resolved the same way.

Binary entries use `binary_mode = "copy"` by default. Set it to `"symlink"`
to create an absolute symbolic link to a large binary, or `"hardlink"` to
create a hard link without duplicating its data. Link sources must already be
executable. Symbolic links depend on the original path remaining available;
hard links require the source and deployment prefix to be on the same
filesystem.

```toml
[[tools]]
type = "binary"
name = "large-solver"
binary = "/shared/build/large-solver"
binary_mode = "symlink"
```

For a Python tool, set `with_executables_from` to expose executable entry
points from its dependencies as well. It is a list of package names and maps to
uv's `--with-executables-from=package1,package2` option.

Set `expose_python` on a Python tool to add a named command that launches the
Python interpreter from that tool's isolated uv environment. Scripts run with
this command can import the same packages as the installed tool:

```toml
[[tools]]
type = "python"
name = "ruff"
package = "ruff==0.8.0"
expose_python = "ruff-python"
```

```sh
module load dev-tools
ruff-python analysis.py
```

Using `expose_python = "python"` deliberately makes `python` resolve to that
tool environment while the module is loaded. A collective manifest may expose
each command name only once, and exposed names cannot match a tool name or an
existing executable. Tool-specific names are safer when several isolated
Python tools share one module.

Set `editable = true` to install the Python tool's package in editable mode.
Use `with_editable = ["/path/to/package"]` to add extra editable packages.
Use `with = ["package==1"]`, `with_requirements = ["requirements.txt"]`,
`overrides = ["overrides.txt"]`, and `lfs = true` for the corresponding uv
options. Relative requirement and override file paths are resolved relative to
the manifest.

Set `verbose` to an integer for repeated `-v` flags. `native_tls = true` and
`no_config = true` pass through their corresponding uv runtime controls; use
the existing `uv_config_file` key for an explicit uv configuration file.

## Shared Tool Defaults

Use `[defaults.python]` to set Python options once for every Python tool in the
manifest. A field written directly in a `[[tools]]` entry replaces its default;
lists are replaced rather than combined, and falsey values such as `false`, `0`,
and `[]` are explicit overrides.

```toml
[defaults.python]
python = "3.13"
indexes = ["https://packages.example/simple"]
constraints = ["constraints.txt"]
native_tls = true
no_cache = true

[[tools]]
type = "python"
name = "ruff"
package = "ruff==0.8.0"

[[tools]]
type = "python"
name = "mypy"
package = "mypy==1.18.2"
python = "3.14"
no_cache = false
```

All reusable Python deployment options can be defaults. Tool identity and
package fields—including `type`, `name`, `version`, and `package`—must remain in
each tool entry. `expose_python` is also per-tool because it claims a unique
command name. Relative paths in defaults are resolved from the manifest, and
`{NAME}` substitution applies before defaults are inherited.

Binary entries can share their installation mode in `[defaults.binary]`:

```toml
[defaults.binary]
binary_mode = "symlink"
```

Individual binary entries can override `binary_mode`. Script entries currently
have no reusable type-specific settings, so there is no `defaults.script`
table.

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

Existing environment versions are left untouched by default. Add `--force` to
deliberately replace one.

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

## Manifest variables

Use `{NAME}` placeholders in manifest string values and set their values with
repeatable `--set NAME=VALUE` options. This is useful when an environment
version, a Python tool version, its package pin, and an exported variable all
share the version from a project's `pyproject.toml`:

```toml
name = "release-tools"
version = "{version}"

[environment]
RELEASE_TOOLS_VERSION = "{version}"

[[tools]]
type = "python"
name = "release-tools"
version = "{version}"
package = "release-tools=={version}"
```

```sh
VERSION=$(uv run python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
module-manager deploy-env --file release-tools.toml --set version="$VERSION"
```

Every placeholder must have a matching `--set` value; an unset or malformed
placeholder is an error. Use `{{` and `}}` for literal braces. Substitution
applies only to TOML string values, never table keys or non-string values.
