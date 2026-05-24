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
    """Resolved defaults loaded from files and environment variables.

    Attributes:
        prefix: Default installation prefix for deployed tools.
        module_root: Default root directory for generated modulefiles.
        indexes: Default Python package indexes passed to `uv tool install`.
        find_links: Default Python package locations passed to
            `uv tool install`.
        uv_config_file: Default uv configuration file passed to `uv tool`.
    """

    prefix: Path | None = None
    module_root: Path | None = None
    indexes: tuple[str, ...] = ()
    find_links: tuple[str, ...] = ()
    uv_config_file: Path | None = None


def default_config_path() -> Path:
    """Return the default per-user config path.

    Returns:
        Expanded path to the default TOML configuration file.
    """
    return DEFAULT_CONFIG_PATH.expanduser()


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from TOML and overlay environment variables.

    Args:
        path: Optional TOML configuration path. When omitted, the per-user
            default path is used.

    Returns:
        Resolved application configuration.

    Raises:
        TypeError: If a configured TOML value has the wrong type.
    """
    config_path = (path or default_config_path()).expanduser()
    file_config = load_file_config(config_path)
    return overlay_env_config(file_config)


def load_file_config(path: Path) -> AppConfig:
    """Load configuration defaults from a TOML file if it exists.

    Args:
        path: TOML configuration file path.

    Returns:
        Configuration loaded from the file, or empty defaults when the file does
        not exist.

    Raises:
        TypeError: If a configured TOML value has the wrong type.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    if not path.exists():
        return AppConfig()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    python_data = table(data.get("python"), "python")
    return AppConfig(
        prefix=optional_path(data.get("prefix"), "prefix"),
        module_root=optional_path(data.get("module_root"), "module_root"),
        indexes=string_tuple(python_data.get("indexes"), "python.indexes"),
        find_links=string_tuple(python_data.get("find_links"), "python.find_links"),
        uv_config_file=optional_path(python_data.get("uv_config_file"), "python.uv_config_file"),
    )


def overlay_env_config(config: AppConfig) -> AppConfig:
    """Apply `MODULE_MANAGER_*` environment variables to file config.

    Args:
        config: Base configuration loaded from TOML.

    Returns:
        Configuration with environment values taking precedence.
    """
    return AppConfig(
        prefix=env_path("MODULE_MANAGER_PREFIX") or config.prefix,
        module_root=env_path("MODULE_MANAGER_MODULE_ROOT") or config.module_root,
        indexes=env_tuple("MODULE_MANAGER_INDEXES") or env_tuple("MODULE_MANAGER_INDEX") or config.indexes,
        find_links=env_tuple("MODULE_MANAGER_FIND_LINKS") or config.find_links,
        uv_config_file=config.uv_config_file,
    )


def table(value: object, key: str) -> dict[str, Any]:
    """Return a TOML table or raise a useful type error.

    Args:
        value: Raw TOML value.
        key: Configuration key used in error messages.

    Returns:
        A TOML table as a dictionary, or an empty dictionary when `value` is
        `None`.

    Raises:
        TypeError: If `value` is not a TOML table.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    msg = f"{key} must be a TOML table"
    raise TypeError(msg)


def optional_path(value: object, key: str) -> Path | None:
    """Parse an optional TOML string as a path.

    Args:
        value: Raw TOML value.
        key: Configuration key used in error messages.

    Returns:
        Expanded path when configured, otherwise `None`.

    Raises:
        TypeError: If `value` is neither `None` nor a string.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return Path(value).expanduser()
    msg = f"{key} must be a string"
    raise TypeError(msg)


def string_tuple(value: object, key: str) -> tuple[str, ...]:
    """Parse an optional TOML string list.

    Args:
        value: Raw TOML value.
        key: Configuration key used in error messages.

    Returns:
        Tuple of configured strings, or an empty tuple when `value` is `None`.

    Raises:
        TypeError: If `value` is not a list of strings.
    """
    if value is None:
        return ()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    msg = f"{key} must be a list of strings"
    raise TypeError(msg)


def env_path(name: str) -> Path | None:
    """Read a path from an environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Expanded path when the variable is set and non-empty, otherwise `None`.
    """
    value = os.environ.get(name)
    if not value:
        return None
    return Path(value).expanduser()


def env_tuple(name: str) -> tuple[str, ...]:
    """Read comma-separated string values from an environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Tuple of non-empty comma-separated values with surrounding whitespace
        removed.
    """
    value = os.environ.get(name)
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())
