"""CLI behavior tests for module-manager."""

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from module_manager.cli import main
from module_manager.deploy import ConstraintGenerationResult

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
    assert "[cyan]" not in output


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
                "--with",
                "ruff-lsp==0.1",
                "--with-requirements",
                "/prod/requirements.txt",
                "--editable",
                "--with-editable",
                "ruff-lsp",
                "--with-editable",
                "ruff-format",
                "--with-executables-from=ruff-lsp,ruff-format",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
                "--index",
                "https://packages.example/simple",
                "--default-index",
                "https://default.example/simple",
                "--find-links",
                "/prod/wheels",
                "--no-index",
                "--index-strategy",
                "unsafe-first-match",
                "--keyring-provider",
                "subprocess",
                "--constraints",
                "/prod/constraints.txt",
                "--overrides",
                "/prod/overrides.txt",
                "--no-cache",
                "--refresh",
                "--refresh-package",
                "ruff",
                "--force",
                "--reinstall",
                "--lfs",
                "-vv",
                "--native-tls",
                "--no-config",
                "--config-file",
                "/prod/uv.toml",
                "--uv-executable",
                "/opt/uv/bin/uv",
            ],
        )
        modulefile = Path("modules/ruff/0.8.0").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "modulefile: modules/ruff/0.8.0" in result.output
    assert "default version: modules/ruff/.version" in result.output
    assert "--config-file /prod/uv.toml" in modulefile
    assert "/opt/uv/bin/uv -v -v --native-tls --no-config tool --config-file /prod/uv.toml install" in modulefile
    assert "/opt/uv/bin/uv -v -v --native-tls --no-config tool" in modulefile
    assert "--default-index https://default.example/simple" in modulefile
    assert "--no-index" in modulefile
    assert "--index-strategy unsafe-first-match" in modulefile
    assert "--keyring-provider subprocess" in modulefile
    assert "--constraints /prod/constraints.txt" in modulefile
    assert "--with ruff-lsp==0.1" in modulefile
    assert "--with-requirements /prod/requirements.txt" in modulefile
    assert "--overrides /prod/overrides.txt" in modulefile
    assert "--no-cache" in modulefile
    assert "--refresh" in modulefile
    assert "--refresh-package ruff" in modulefile
    assert "--force" in modulefile
    assert "--reinstall" in modulefile
    assert "--lfs" in modulefile
    assert "--editable" in modulefile
    assert "--with-editable ruff-lsp" in modulefile
    assert "--with-editable ruff-format" in modulefile
    assert "--with-executables-from=ruff-lsp,ruff-format" in modulefile


def test_deploy_python_uses_project_dependencies_for_executable_sources() -> None:
    """A bare executable-source option should read project dependencies."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path("pyproject.toml").write_text(
            '[project]\ndependencies = ["click>=8.1", "rich-click>=1.8"]\n',
            encoding="utf-8",
        )
        result = runner.invoke(
            main,
            [
                "deploy-python",
                "my-tool",
                "1.0.0",
                "--package",
                "my-tool==1.0.0",
                "--with-executables-from",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )
        modulefile = Path("modules/my-tool/1.0.0").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "--with-executables-from=click,rich-click" in modulefile


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
uv_executable = "bin/uv"
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
    assert "bin/uv tool --config-file uv.toml install" in modulefile


def test_deploy_command_rejects_matching_prefix_and_module_root() -> None:
    """Deployment roots must differ to avoid a modulefile path collision."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "deploy-python",
                "gitconductor",
                "0.7.0",
                "--package",
                "gitconductor",
                "--prefix",
                "test",
                "--module-root",
                "test",
            ],
        )
        collision_path_exists = Path("test/gitconductor/0.7.0").exists()

    assert result.exit_code != 0
    output = " ".join(strip_ansi(result.output).split())
    assert "--module-root and --prefix must resolve to different directories" in output
    assert not collision_path_exists


def test_auto_constraints_command_writes_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """The auto-constraints command should report the generated file.

    Args:
        monkeypatch: Pytest helper used to replace constraint generation.
    """
    runner = CliRunner()
    calls: list[dict[str, object]] = []

    def fake_generate_constraints(**kwargs: object) -> ConstraintGenerationResult:
        """Record generation options."""
        calls.append(kwargs)
        return ConstraintGenerationResult(
            output_file=Path("constraints.txt"),
            requirements=("url-tool", "url-dep @ file:///tmp/url-dep"),
            discovered_url_dependencies=("url-dep @ file:///tmp/url-dep",),
            iterations=2,
        )

    monkeypatch.setattr("module_manager.cli.generate_constraints", fake_generate_constraints)

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "auto-constraints",
                "url-tool",
                "--index",
                "https://packages.example/simple",
                "--output",
                "constraints.txt",
            ],
        )

    assert result.exit_code == 0
    assert calls == [
        {
            "package": "url-tool",
            "output_file": Path("constraints.txt"),
            "python": None,
            "indexes": ("https://packages.example/simple",),
            "default_index": None,
            "find_links": (),
            "no_index": False,
            "index_strategy": None,
            "keyring_provider": None,
            "uv_config_file": None,
            "uv_executable": None,
        }
    ]
    assert "constraints: constraints.txt" in result.output
    assert "discovered URL dependencies: 1" in result.output
    assert "url-dep @ file:///tmp/url-dep" in result.output


def test_auto_constraints_command_accepts_resolver_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """The auto-constraints command should expose deployment-equivalent resolver options.

    Args:
        monkeypatch: Pytest helper used to replace constraint generation.
    """
    runner = CliRunner()
    calls: list[dict[str, object]] = []

    def fake_generate_constraints(**kwargs: object) -> ConstraintGenerationResult:
        """Record generation options."""
        calls.append(kwargs)
        return ConstraintGenerationResult(
            output_file=Path("constraints.txt"),
            requirements=("internal-tool",),
            discovered_url_dependencies=(),
            iterations=1,
        )

    monkeypatch.setattr("module_manager.cli.generate_constraints", fake_generate_constraints)

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "auto-constraints",
                "internal-tool",
                "--default-index",
                "https://default.example/simple",
                "--no-index",
                "--index-strategy",
                "unsafe-best-match",
                "--keyring-provider",
                "subprocess",
            ],
        )

    assert result.exit_code == 0
    assert calls[0]["default_index"] == "https://default.example/simple"
    assert calls[0]["no_index"] is True
    assert calls[0]["index_strategy"] == "unsafe-best-match"
    assert calls[0]["keyring_provider"] == "subprocess"


def test_deploy_python_missing_uv_reports_click_error() -> None:
    """Missing uv executables should be reported without a traceback."""
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
                "--execute-install",
                "--uv-executable",
                "missing-uv",
            ],
        )
        install_root_exists = Path("tools/ruff/0.8.0").exists()

    assert result.exit_code != 0
    assert "Required executable not found on PATH: missing-uv" in strip_ansi(result.output)
    assert "Traceback" not in result.output
    assert not install_root_exists


def test_deploy_script_missing_file_is_a_usage_error() -> None:
    """Missing script paths should fail during option validation."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "deploy-script",
                "hello",
                "1.0.0",
                "--script",
                "missing.sh",
                "--prefix",
                "tools",
                "--module-root",
                "modules",
            ],
        )

    assert result.exit_code != 0
    assert "does not exist" in strip_ansi(result.output)
    assert "Traceback" not in result.output


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
with = ["ruff-lsp==0.1"]
with_requirements = ["requirements.txt"]
indexes = ["https://packages.example/simple"]
default_index = "https://default.example/simple"
no_index = true
constraints = ["constraints.txt"]
overrides = ["overrides.txt"]
no_cache = true
refresh = true
refresh_packages = ["ruff"]
force = true
lfs = true
verbose = 2
native_tls = true
no_config = true
editable = true
with_editable = ["ruff-lsp", "ruff-format"]
with_executables_from = ["ruff-lsp", "ruff-format"]
uv_executable = "bin/uv"
""".strip(),
            encoding="utf-8",
        )
        result = runner.invoke(main, ["deploy-env", "--file", str(manifest), "--dry-run"])
        install_root_exists = Path("tools/dev-tools/2026.05").exists()

    assert result.exit_code == 0
    assert "would create install root: tools/dev-tools/2026.05" in result.output
    assert "would install python ruff:" in result.output
    assert "--index https://packages.example/simple" in result.output
    assert "--default-index https://default.example/simple" in result.output
    assert "--no-index" in result.output
    assert "--constraints constraints.txt" in result.output
    assert "--with ruff-lsp==0.1" in result.output
    assert "--with-requirements requirements.txt" in result.output
    assert "--overrides overrides.txt" in result.output
    assert "--no-cache" in result.output
    assert "--refresh" in result.output
    assert "--refresh-package ruff" in result.output
    assert "--force" in result.output
    assert "--lfs" in result.output
    assert "-v -v --native-tls --no-config" in result.output
    assert "--editable" in result.output
    assert "--with-editable ruff-lsp" in result.output
    assert "--with-editable ruff-format" in result.output
    assert "--with-executables-from=ruff-lsp,ruff-format" in result.output
    assert "bin/uv -v -v --native-tls --no-config tool install" in result.output
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
