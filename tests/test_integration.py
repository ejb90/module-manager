"""Integration tests that execute external deployment tools."""

import subprocess
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
            "0.7.0",
            "--package",
            str(project_root),
            "--prefix",
            str(prefix),
            "--module-root",
            str(module_root),
            "--execute-install",
        ],
    )

    install_root = prefix / "module-manager" / "0.7.0"
    assert result.exit_code == 0, result.output
    assert (install_root / "bin" / "module-manager").exists()
    assert (install_root / "uv-tools" / "env-module-manager" / "uv-receipt.toml").exists()
    assert (module_root / "module-manager" / "0.7.0").is_file()
    assert not inherited_tool_dir.exists()
    assert not inherited_bin_dir.exists()


@pytest.mark.integration
def test_deploy_python_real_uv_install_handles_url_dependency(tmp_path: Path) -> None:
    """A real uv install should resolve and run direct URL dependencies.

    Args:
        tmp_path: Temporary deployment root.
    """
    dependency = tmp_path / "url-dependency"
    dependency.mkdir()
    (dependency / "pyproject.toml").write_text(
        """
[project]
name = "url-dependency"
version = "1.0.0"
requires-python = ">=3.11"
""".strip(),
        encoding="utf-8",
    )
    dependency_package = dependency / "url_dependency"
    dependency_package.mkdir()
    (dependency_package / "__init__.py").write_text(
        """
def message() -> str:
    return "url dependency works"
""".strip(),
        encoding="utf-8",
    )

    tool = tmp_path / "url-tool"
    tool.mkdir()
    (tool / "pyproject.toml").write_text(
        f"""
[project]
name = "url-tool"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "url-dependency @ {dependency.as_uri()}",
]

[project.scripts]
url-tool = "url_tool:main"
""".strip(),
        encoding="utf-8",
    )
    tool_package = tool / "url_tool"
    tool_package.mkdir()
    (tool_package / "__init__.py").write_text(
        """
from url_dependency import message


def main() -> None:
    print(message())
""".strip(),
        encoding="utf-8",
    )

    prefix = tmp_path / "tools"
    module_root = tmp_path / "modules"
    result = CliRunner().invoke(
        main,
        [
            "deploy-python",
            "url-tool",
            "1.0.0",
            "--package",
            str(tool),
            "--prefix",
            str(prefix),
            "--module-root",
            str(module_root),
            "--execute-install",
        ],
    )

    executable = prefix / "url-tool" / "1.0.0" / "bin" / "url-tool"
    assert result.exit_code == 0, result.output
    assert executable.exists()
    completed = subprocess.run(
        [str(executable)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "url dependency works"
