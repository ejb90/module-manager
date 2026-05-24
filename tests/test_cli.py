"""CLI behavior tests for module-manager."""

import re
from pathlib import Path

from click.testing import CliRunner

from module_manager.cli import main

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def strip_ansi(value: str) -> str:
    """Remove ANSI escape sequences from terminal output.

    Args:
        value: Text that may contain ANSI escape sequences.

    Returns:
        Text with ANSI escape sequences removed.
    """
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
                "--uv-config-file",
                "/prod/uv.toml",
            ],
        )
        modulefile = Path("modules/ruff/0.8.0").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "modulefile: modules/ruff/0.8.0" in result.output
    assert "default version: modules/ruff/.version" in result.output
    assert "--config-file /prod/uv.toml" in modulefile


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
uv_config_file = "uv.toml"
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
        modulefile = Path("modules/ruff/0.8.0").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "modulefile: modules/ruff/0.8.0" in result.output
    assert "--config-file uv.toml" in modulefile


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


def test_deploy_rust_command_dry_run_does_not_write_files() -> None:
    """Dry-run Rust deployment should report paths without creating them."""
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
                "--dry-run",
            ],
        )
        install_root_exists = Path("tools/ripgrep/14.1.1").exists()
        modulefile_exists = Path("modules/ripgrep/14.1.1").exists()

    assert result.exit_code == 0
    assert "would write modulefile: modules/ripgrep/14.1.1" in result.output
    assert not install_root_exists
    assert not modulefile_exists


def test_deploy_script_command_copies_script() -> None:
    """The script deploy command should copy the script and report the modulefile."""
    runner = CliRunner()

    with runner.isolated_filesystem() as fs:
        script = Path(fs) / "hello.sh"
        script.write_text("#!/usr/bin/env bash\necho hello\n", encoding="utf-8")
        result = runner.invoke(
            main,
            [
                "deploy-script",
                "hello",
                "1.0.0",
                "--script",
                str(script),
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )

        deployed = Path("tools/hello/1.0.0/bin/hello")
        deployed_exists = deployed.exists()
        deployed_is_executable = bool(deployed.stat().st_mode & 0o111)

    assert result.exit_code == 0
    assert "modulefile: modules/hello/1.0.0" in result.output
    assert deployed_exists
    assert deployed_is_executable


def test_deploy_script_command_dry_run_does_not_write_files() -> None:
    """Dry-run script deployment should report paths without creating them."""
    runner = CliRunner()

    with runner.isolated_filesystem() as fs:
        script = Path(fs) / "hello.sh"
        script.write_text("#!/usr/bin/env bash\necho hello\n", encoding="utf-8")
        result = runner.invoke(
            main,
            [
                "deploy-script",
                "hello",
                "1.0.0",
                "--script",
                str(script),
                "--prefix",
                "tools",
                "--module-root",
                "modules",
                "--dry-run",
            ],
        )
        deployed_exists = Path("tools/hello/1.0.0/bin/hello").exists()
        modulefile_exists = Path("modules/hello/1.0.0").exists()

    assert result.exit_code == 0
    assert "would write modulefile: modules/hello/1.0.0" in result.output
    assert not deployed_exists
    assert not modulefile_exists


def test_deploy_command_can_skip_default_version() -> None:
    """The shared --no-default option should skip writing the default selector."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "deploy-rust",
                "ripgrep",
                "14.1.1",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
                "--no-default",
            ],
        )
        default_file_exists = Path("modules/ripgrep/.version").exists()

    assert result.exit_code == 0
    assert "default version:" not in result.output
    assert not default_file_exists


def test_uninstall_command_removes_deployed_version() -> None:
    """The uninstall command should remove the install tree and modulefile."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        deploy_result = runner.invoke(
            main,
            [
                "deploy-rust",
                "ripgrep",
                "14.1.1",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )
        uninstall_result = runner.invoke(
            main,
            [
                "uninstall",
                "ripgrep",
                "14.1.1",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )
        install_root_exists = Path("tools/ripgrep/14.1.1").exists()
        modulefile_exists = Path("modules/ripgrep/14.1.1").exists()
        default_file_exists = Path("modules/ripgrep/.version").exists()

    assert deploy_result.exit_code == 0
    assert uninstall_result.exit_code == 0
    assert "removed: tools/ripgrep/14.1.1" in uninstall_result.output
    assert "removed: modules/ripgrep/14.1.1" in uninstall_result.output
    assert "removed: modules/ripgrep/.version" in uninstall_result.output
    assert not install_root_exists
    assert not modulefile_exists
    assert not default_file_exists


def test_uninstall_command_dry_run_preserves_deployed_version() -> None:
    """Dry-run uninstall should report targets while preserving files."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        runner.invoke(
            main,
            [
                "deploy-rust",
                "ripgrep",
                "14.1.1",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )
        result = runner.invoke(
            main,
            [
                "uninstall",
                "ripgrep",
                "14.1.1",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
                "--dry-run",
            ],
        )
        install_root_exists = Path("tools/ripgrep/14.1.1").exists()

    assert result.exit_code == 0
    assert "would remove: tools/ripgrep/14.1.1" in result.output
    assert install_root_exists


def test_deploy_env_command_dry_run_reads_manifest() -> None:
    """Dry-run environment deployment should report manifest actions only."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        manifest = Path("env.toml")
        manifest.write_text(
            """
name = "dev-tools"
version = "2026.05"
prefix = "tools"
module_root = "modules"

[[tools]]
type = "python"
name = "ruff"
version = "0.8.0"
package = "ruff==0.8.0"
indexes = ["https://packages.example/simple"]
""".strip(),
            encoding="utf-8",
        )
        result = runner.invoke(main, ["deploy-env", "--file", str(manifest), "--dry-run"])
        install_root_exists = Path("tools/dev-tools/2026.05").exists()

    assert result.exit_code == 0
    assert "would create install root: tools/dev-tools/2026.05" in result.output
    assert "would install python ruff:" in result.output
    assert "--index https://packages.example/simple" in result.output
    assert not install_root_exists


def test_deploy_env_command_reports_invalid_manifest() -> None:
    """Invalid environment manifests should produce a Click error."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        manifest = Path("env.toml")
        manifest.write_text('name = "broken"\n', encoding="utf-8")
        result = runner.invoke(main, ["deploy-env", "--file", str(manifest)])

    assert result.exit_code != 0
    assert "tools must be a list of tables" in result.output


def test_deploy_env_command_writes_collective_module() -> None:
    """Environment deployment should copy tools into one shared module."""
    runner = CliRunner()

    with runner.isolated_filesystem() as fs:
        binary = Path(fs) / "rg"
        script = Path(fs) / "hello.sh"
        binary.write_text("binary", encoding="utf-8")
        script.write_text("#!/usr/bin/env bash\necho hello\n", encoding="utf-8")
        manifest = Path("env.toml")
        manifest.write_text(
            f"""
name = "dev-tools"
version = "2026.05"
prefix = "tools"
module_root = "modules"

[[tools]]
type = "rust"
name = "ripgrep"
version = "14.1.1"
binary = "{binary}"

[[tools]]
type = "script"
name = "hello"
version = "1.0.0"
script = "{script}"
""".strip(),
            encoding="utf-8",
        )
        result = runner.invoke(main, ["deploy-env", "--file", str(manifest)])
        ripgrep_exists = Path("tools/dev-tools/2026.05/bin/ripgrep").exists()
        hello_exists = Path("tools/dev-tools/2026.05/bin/hello").exists()
        modulefile_exists = Path("modules/dev-tools/2026.05").exists()

    assert result.exit_code == 0
    assert "create install root: tools/dev-tools/2026.05" in result.output
    assert ripgrep_exists
    assert hello_exists
    assert modulefile_exists
