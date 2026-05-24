# Configuration

`module-manager` reads defaults in this order, from lowest to highest priority:

1. `~/.config/module-manager/config.toml`
2. `MODULE_MANAGER_*` environment variables
3. CLI options

## TOML Config

Create `~/.config/module-manager/config.toml`:

```toml
prefix = "/prod/tools"
module_root = "/prod/modulefiles"

[python]
indexes = ["https://packages.example/simple"]
find_links = ["/prod/wheels"]
uv_config_file = "/prod/config/uv.toml"
```

Use a different config file with `--config`:

```sh
module-manager --config ./module-manager.toml deploy-python ...
```

## Environment Variables

```sh
export MODULE_MANAGER_PREFIX=/prod/tools
export MODULE_MANAGER_MODULE_ROOT=/prod/modulefiles
export MODULE_MANAGER_INDEXES=https://packages.example/simple,https://mirror.example/simple
export MODULE_MANAGER_FIND_LINKS=/prod/wheels,/prod/more-wheels
```

`MODULE_MANAGER_CONFIG` can point to an alternate TOML config file.

There is no `MODULE_MANAGER_*` environment variable for uv configuration files.
Use uv's own `UV_CONFIG_FILE` environment variable when you want to set that via
the environment.

## CLI Precedence

CLI options override both environment variables and TOML config:

```sh
module-manager deploy-rust ripgrep 14.1.1 \
  --prefix /scratch/tools \
  --module-root /scratch/modulefiles
```
