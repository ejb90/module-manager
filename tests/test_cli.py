"""CLI behavior tests for module-manager."""

import re
from pathlib import Path

from click.testing import CliRunner

from module_manager.cli import main

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def strip_ansi(value: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return ANSI_ESCAPE_RE.sub("", value)


def test_help_uses_rich_click_formatting() -> None:
    """The top-level help output should use Rich Click panels."""
    runner = CliRunner()

    result = runner.invoke(main, ["--help"])
    output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert "Options" in output
    assert "Commands" in output
    assert "Examples:" in output


def test_deploy_python_command_writes_modulefile() -> None:
    """The Python deploy command should write a modulefile and report its path."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "deploy-python",
                "ruff",
                "0.8.0",
                "--package",
                "ruff==0.8.0",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
                "--index",
                "https://packages.example/simple",
                "--find-links",
                "/prod/wheels",
            ],
        )

    assert result.exit_code == 0
    assert "modulefile: modules/ruff/0.8.0" in result.output


def test_deploy_python_command_uses_config_defaults() -> None:
    """The Python deploy command should read prefix defaults from TOML."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        config = Path("config.toml")
        config.write_text(
            """
prefix = "tools"
module_root = "modules"

[python]
indexes = ["https://packages.example/simple"]
find_links = ["/prod/wheels"]
""".strip(),
            encoding="utf-8",
        )
        result = runner.invoke(
            main,
            [
                "--config",
                str(config),
                "deploy-python",
                "ruff",
                "0.8.0",
                "--package",
                "ruff==0.8.0",
            ],
        )

    assert result.exit_code == 0
    assert "modulefile: modules/ruff/0.8.0" in result.output


def test_cli_options_override_config_defaults() -> None:
    """CLI options should take precedence over configured defaults."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        config = Path("config.toml")
        config.write_text(
            """
prefix = "config-tools"
module_root = "config-modules"
""".strip(),
            encoding="utf-8",
        )
        result = runner.invoke(
            main,
            [
                "--config",
                str(config),
                "deploy-rust",
                "ripgrep",
                "14.1.1",
                "--prefix",
                "cli-tools",
                "--module-root",
                "cli-modules",
            ],
        )

    assert result.exit_code == 0
    assert "modulefile: cli-modules/ripgrep/14.1.1" in result.output


def test_deploy_rust_command_copies_binary() -> None:
    """The Rust deploy command should copy the binary and report the modulefile."""
    runner = CliRunner()

    with runner.isolated_filesystem() as fs:
        binary = Path(fs) / "rg"
        binary.write_text("binary", encoding="utf-8")
        result = runner.invoke(
            main,
            [
                "deploy-rust",
                "ripgrep",
                "14.1.1",
                "--binary",
                str(binary),
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )

    assert result.exit_code == 0
    assert "modulefile: modules/ripgrep/14.1.1" in result.output
