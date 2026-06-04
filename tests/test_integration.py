"""Integration tests that execute external deployment tools."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from module_manager.cli import main


@pytest.mark.integration
def test_deploy_python_real_uv_install_uses_cli_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A real uv install should use the CLI prefix and module root.

    Args:
        tmp_path: Temporary deployment root.
        monkeypatch: Pytest helper used to control inherited uv destinations.
    """
    project_root = Path(__file__).parent.parent
    prefix = tmp_path / "tools"
    module_root = tmp_path / "modules"
    inherited_tool_dir = tmp_path / "inherited-tools"
    inherited_bin_dir = tmp_path / "inherited-bin"
    monkeypatch.setenv("UV_TOOL_DIR", str(inherited_tool_dir))
    monkeypatch.setenv("UV_TOOL_BIN_DIR", str(inherited_bin_dir))

    result = CliRunner().invoke(
        main,
        [
            "deploy-python",
            "module-manager",
            "0.5.0",
            "--package",
            str(project_root),
            "--prefix",
            str(prefix),
            "--module-root",
            str(module_root),
            "--execute-install",
        ],
    )

    install_root = prefix / "module-manager" / "0.5.0"
    assert result.exit_code == 0, result.output
    assert (install_root / "bin" / "module-manager").exists()
    assert (install_root / "uv-tools" / "env-module-manager" / "uv-receipt.toml").exists()
    assert (module_root / "module-manager" / "0.5.0").is_file()
    assert not inherited_tool_dir.exists()
    assert not inherited_bin_dir.exists()
