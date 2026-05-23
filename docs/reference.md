# CLI Reference

Show top-level help:

```sh
module-manager --help
```

Show Python deployment options:

```sh
module-manager deploy-python --help
```

Show Rust deployment options:

```sh
module-manager deploy-rust --help
```

Show shell script deployment options:

```sh
module-manager deploy-script --help
```

Show uninstall options:

```sh
module-manager uninstall --help
```

## Python Command

```sh
module-manager deploy-python NAME VERSION \
  --package PACKAGE \
  [--python PYTHON] \
  [--index URL] \
  [--find-links PATH_OR_URL] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default] \
  [--execute-install]
```

## Rust Command

```sh
module-manager deploy-rust NAME VERSION \
  [--binary PATH] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default]
```

## Shell Script Command

```sh
module-manager deploy-script NAME VERSION \
  [--script PATH] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default]
```

## Uninstall Command

```sh
module-manager uninstall NAME VERSION \
  [--prefix PATH] \
  [--module-root PATH] \
  [--keep-default] \
  [--dry-run]
```
