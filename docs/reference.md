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

Show collective environment deployment options:

```sh
module-manager deploy-env --help
```

Show constraint generation options:

```sh
module-manager auto-constraints --help
```

Show uninstall options:

```sh
module-manager uninstall --help
```

## Python Command

```sh
module-manager deploy-python NAME VERSION \
  --package PACKAGE \
  [--with PACKAGE] \
  [--with-requirements PATH] \
  [--editable] \
  [--with-editable PACKAGE] \
  [--with-executables-from [PACKAGES]] \
  [--python PYTHON] \
  [--index URL] \
  [--default-index URL] \
  [--find-links PATH_OR_URL] \
  [--no-index] \
  [--index-strategy STRATEGY] \
  [--keyring-provider PROVIDER] \
  [--constraints PATH] \
  [--overrides PATH] \
  [--no-cache] \
  [--refresh] \
  [--refresh-package PACKAGE] \
  [--force] \
  [--reinstall] \
  [--lfs] \
  [-v|--verbose] \
  [--native-tls] \
  [--no-config] \
  [--config-file PATH] \
  [--uv-config-file PATH] \
  [--uv-executable PATH] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default] \
  [--execute-install]
```

## Auto-Constraints Command

```sh
module-manager auto-constraints PACKAGE \
  [--output PATH] \
  [--python PYTHON] \
  [--index URL] \
  [--default-index URL] \
  [--find-links PATH_OR_URL] \
  [--no-index] \
  [--index-strategy STRATEGY] \
  [--keyring-provider PROVIDER] \
  [--uv-config-file PATH] \
  [--uv-executable PATH]
```

## Rust Command

```sh
module-manager deploy-rust NAME VERSION \
  [--binary PATH] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default] \
  [--dry-run]
```

## Shell Script Command

```sh
module-manager deploy-script NAME VERSION \
  [--script PATH] \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default] \
  [--dry-run]
```

## Collective Environment Command

```sh
module-manager deploy-env \
  --file MANIFEST.toml \
  [--prefix PATH] \
  [--module-root PATH] \
  [--no-default] \
  [--dry-run]
```

## Uninstall Command

```sh
module-manager uninstall NAME VERSION \
  [--prefix PATH] \
  [--module-root PATH] \
  [--keep-default] \
  [--dry-run]
```
