# Changelog

All notable changes to this project are documented in this file.

## [0.18.0] - 2026-11-03

### Changed

- Make Python deployments install immediately by default; use `--metadata-only`
  to defer `uv tool install`.
- Reserve `--force` for replacing deployments and use `--uv-force` or
  manifest `uv_force` to pass `--force` to uv.

## [0.17.0] - 2026-11-03

### Added

- Add Python 3.15 support and test it in continuous integration.

## [0.16.0] - 2026-11-03

### Added

- Add `deploy-env --set NAME=VALUE` manifest substitutions for shared values
  such as an environment version, Python package pin, and exported variables.
