# Uninstall

Remove one deployed tool version with the `uninstall` command:

```sh
module-manager uninstall ruff 0.8.0 \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

This removes:

```text
/prod/tools/ruff/0.8.0
/prod/modulefiles/ruff/0.8.0
```

If the default selector points at the same version, it is removed too:

```text
/prod/modulefiles/ruff/.version
```

If the default selector points at a different version, it is left in place.

Preview an uninstall without deleting files:

```sh
module-manager uninstall ruff 0.8.0 \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --dry-run
```

Leave the default selector untouched even when it points at the removed version:

```sh
module-manager uninstall ruff 0.8.0 \
  --prefix /prod/tools \
  --module-root /prod/modulefiles \
  --keep-default
```
