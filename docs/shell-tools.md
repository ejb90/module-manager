# Shell Scripts

Shell scripts can be copied directly into the versioned prefix.

```sh
module-manager deploy-script my-tool 1.0.0 \
  --script ./scripts/my-tool \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

This writes the script to:

```text
/prod/tools/my-tool/1.0.0/bin/my-tool
```

and creates:

```text
/prod/modulefiles/my-tool/1.0.0
```

The deployed script is marked executable, and the generated modulefile prepends
the deployed `bin` directory to `PATH`.

Deployments make the deployed version the module default, so `module load
my-tool` resolves to `my-tool/1.0.0`. Add `--no-default` to leave the current
default unchanged.

Preview the paths that would be written without copying the script:

```sh
module-manager deploy-script my-tool 1.0.0 \
  --script ./scripts/my-tool \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --dry-run
```
