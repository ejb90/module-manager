# module-manager

`module-manager` deploys versioned Python, Rust, shell, and collective CLI
environments behind GNU environment modulefiles for Linux/HPC systems.

It is designed for administrators who want reproducible command-line tool
installations under a production prefix such as `/prod/tools`, with matching
modulefiles under a module tree such as `/prod/modulefiles`.

## What It Creates

Each tool version gets its own installation root:

```text
/prod/tools/<name>/<version>/
```

The executable directory is exposed through the modulefile:

```text
/prod/tools/<name>/<version>/bin
```

The generated modulefile is written to:

```text
/prod/modulefiles/<name>/<version>
```

Collective environments use the same layout, but several tools share one
versioned `bin` directory and one modulefile.

## Common Workflow

```sh
module-manager deploy-python ruff 0.8.0 \
  --package 'ruff==0.8.0' \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --execute-install

module use /prod/modulefiles
module load ruff/0.8.0
ruff --version
```

## Next Steps

- Install prerequisites in [Installation](installation.md).
- Set shared defaults in [Configuration](configuration.md).
- Deploy Python packages with [Python Tools](python-tools.md).
- Deploy Rust binaries with [Rust Tools](rust-tools.md).
- Deploy shell scripts with [Shell Scripts](shell-tools.md).
- Deploy shared tool bundles with [Collective Environments](collective-environments.md).
- Remove deployed versions with [Uninstall](uninstall.md).
