"""Configuration loading for module-manager."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

DEFAULT_CONFIG_PATH = Path("~/.config/module-manager/config.toml")


@dataclass(frozen=True)
class AppConfig:
    """Resolved defaults loaded from files and environment variables."""

    prefix: Path | None = None
    module_root: Path | None = None
    indexes: tuple[str, ...] = ()
    find_links: tuple[str, ...] = ()


def default_config_path() -> Path:
    """Return the default per-user config path."""
    return DEFAULT_CONFIG_PATH.expanduser()


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from TOML and overlay environment variables."""
    config_path = (path or default_config_path()).expanduser()
    file_config = load_file_config(config_path)
    return overlay_env_config(file_config)


def load_file_config(path: Path) -> AppConfig:
    """Load configuration defaults from a TOML file if it exists."""
    if not path.exists():
        return AppConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    python_data = table(data.get("python"), "python")
    return AppConfig(
        prefix=optional_path(data.get("prefix"), "prefix"),
        module_root=optional_path(data.get("module_root"), "module_root"),
        indexes=string_tuple(python_data.get("indexes"), "python.indexes"),
        find_links=string_tuple(python_data.get("find_links"), "python.find_links"),
    )


def overlay_env_config(config: AppConfig) -> AppConfig:
    """Apply MODULE_MANAGER_* environment variables to file config."""
    return AppConfig(
        prefix=env_path("MODULE_MANAGER_PREFIX") or config.prefix,
        module_root=env_path("MODULE_MANAGER_MODULE_ROOT") or config.module_root,
        indexes=env_tuple("MODULE_MANAGER_INDEXES") or env_tuple("MODULE_MANAGER_INDEX") or config.indexes,
        find_links=env_tuple("MODULE_MANAGER_FIND_LINKS") or config.find_links,
    )


def table(value: object, key: str) -> dict[str, Any]:
    """Return a TOML table or raise a useful type error."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    msg = f"{key} must be a TOML table"
    raise TypeError(msg)


def optional_path(value: object, key: str) -> Path | None:
    """Parse an optional TOML string as a path."""
    if value is None:
        return None
    if isinstance(value, str):
        return Path(value).expanduser()
    msg = f"{key} must be a string"
    raise TypeError(msg)


def string_tuple(value: object, key: str) -> tuple[str, ...]:
    """Parse an optional TOML string list."""
    if value is None:
        return ()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    msg = f"{key} must be a list of strings"
    raise TypeError(msg)


def env_path(name: str) -> Path | None:
    """Read a path from an environment variable."""
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def env_tuple(name: str) -> tuple[str, ...]:
    """Read comma-separated string values from an environment variable."""
    value = os.environ.get(name)
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())
