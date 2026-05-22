# Installation

`module-manager` expects two external command-line tools for a full workflow:

- `uv`, when deploying Python tools with `--execute-install`
- Environment Modules, when loading generated modulefiles

## Install uv

Install `uv` with the official installer:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify it is available:

```sh
uv --version
```

## Install Environment Modules on macOS

On macOS, install Environment Modules with Homebrew:

```sh
brew install modules
```

Initialize it for zsh:

```sh
source "$HOMEBREW_PREFIX/opt/modules/init/zsh"
```

Add that `source` line to `~/.zshrc` if you want the `module` command available
in every new shell.

## Install module-manager

From a local checkout:

```sh
uv tool install .
```

During development, use:

```sh
uv run module-manager --help
```
