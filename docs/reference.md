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

## Python Command

```sh
module-manager deploy-python NAME VERSION \
  --package PACKAGE \
  [--python PYTHON] \
  [--index URL] \
  [--find-links PATH_OR_URL] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--execute-install]
```

## Rust Command

```sh
module-manager deploy-rust NAME VERSION \
  [--binary PATH] \
  [--prefix PATH] \
  [--module-root PATH]
```
