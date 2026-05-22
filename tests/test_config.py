"""Configuration loading tests for module-manager."""

from pathlib import Path

import pytest

from module_manager.config import AppConfig, load_config


def test_load_config_reads_toml_defaults(tmp_path: Path) -> None:
    """Config files should provide deployment defaults."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
prefix = "/scratch/tools"
module_root = "/scratch/modules"

[python]
indexes = ["https://packages.example/simple"]
find_links = ["/scratch/wheels"]
""".strip(),
        encoding="utf-8",
    )

    assert load_config(config_path) == AppConfig(
        prefix=Path("/scratch/tools"),
        module_root=Path("/scratch/modules"),
        indexes=("https://packages.example/simple",),
        find_links=("/scratch/wheels",),
    )


def test_load_config_overlays_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables should override TOML defaults."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
prefix = "/config/tools"
module_root = "/config/modules"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MODULE_MANAGER_PREFIX", "/env/tools")
    monkeypatch.setenv("MODULE_MANAGER_MODULE_ROOT", "/env/modules")
    monkeypatch.setenv("MODULE_MANAGER_INDEXES", "https://one.example/simple,https://two.example/simple")
    monkeypatch.setenv("MODULE_MANAGER_FIND_LINKS", "/env/wheels,/env/more-wheels")

    assert load_config(config_path) == AppConfig(
        prefix=Path("/env/tools"),
        module_root=Path("/env/modules"),
        indexes=("https://one.example/simple", "https://two.example/simple"),
        find_links=("/env/wheels", "/env/more-wheels"),
    )
