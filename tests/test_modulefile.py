"""Modulefile rendering and deployment helper tests."""

import subprocess
from pathlib import Path
from shlex import quote as shlex_quote

import pytest

from module_manager.deploy import (
    MissingExecutableError,
    deploy_environment,
    deploy_python_tool,
    deploy_rust_tool,
    deploy_script_tool,
    discover_url_requirements,
    generate_constraints,
    load_environment_spec,
    require_executable,
    uninstall_tool,
    uv_compile_command,
    uv_install_command,
    uv_install_environment,
)
from module_manager.modulefile import (
    ModuleSpec,
    is_default_version,
    render_default_version,
    render_modulefile,
    tcl_quote,
)


def test_tcl_quote_escapes_special_characters() -> None:
    """Tcl quoting should escape characters that affect modulefile parsing."""
    assert tcl_quote('a "quoted" $value') == '"a \\"quoted\\" \\$value"'


def test_render_modulefile_exports_path_and_root() -> None:
    """Rendered modulefiles should expose PATH and a tool root variable."""
    modulefile = render_modulefile(
        ModuleSpec(
            name="ruff",
            version="0.8.0",
            root=Path("/prod/tools/ruff/0.8.0"),
            bin_dir=Path("/prod/tools/ruff/0.8.0/bin"),
            description="Fast Python linter",
        )
    )

    assert "#%Module1.0" in modulefile
    assert 'module-whatis "Fast Python linter"' in modulefile
    assert "prepend-path PATH $bindir" in modulefile
    assert "setenv RUFF_ROOT $root" in modulefile


def test_render_default_version_selects_version() -> None:
    """Default-version files should select the requested module version."""
    content = render_default_version("0.8.0")

    assert content == '#%Module1.0\nset ModulesVersion "0.8.0"\n'
    assert is_default_version(content, "0.8.0")
    assert not is_default_version(content, "0.9.0")


def test_deploy_python_tool_writes_modulefile(tmp_path: Path) -> None:
    """Python deployments should create the bin directory and modulefile.

    Args:
        tmp_path: Temporary deployment root.
    """
    paths = deploy_python_tool(
        name="ruff",
        version="0.8.0",
        package="ruff==0.8.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    assert paths.modulefile.exists()
    assert paths.bin_dir.is_dir()
    assert paths.default_version_file is not None
    assert 'set ModulesVersion "0.8.0"' in paths.default_version_file.read_text(encoding="utf-8")
    assert "UV_TOOL_DIR=" in paths.modulefile.read_text(encoding="utf-8")


def test_python_tool_install_command_accepts_indexes() -> None:
    """Uv install commands should include custom package source options."""
    assert uv_install_command(
        "internal-tool==1.2.3",
        indexes=("https://packages.example/simple", "https://mirror.example/simple"),
        default_index="https://default.example/simple",
        find_links=("/prod/wheels",),
        no_index=True,
        index_strategy="unsafe-best-match",
        keyring_provider="subprocess",
        constraints=("/prod/constraints.txt",),
        no_cache=True,
        refresh=True,
        refresh_packages=("internal-tool",),
        force=True,
        reinstall=True,
    ) == [
        "uv",
        "tool",
        "install",
        "--index",
        "https://packages.example/simple",
        "--index",
        "https://mirror.example/simple",
        "--default-index",
        "https://default.example/simple",
        "--find-links",
        "/prod/wheels",
        "--no-index",
        "--index-strategy",
        "unsafe-best-match",
        "--keyring-provider",
        "subprocess",
        "--constraints",
        "/prod/constraints.txt",
        "--no-cache",
        "--refresh",
        "--refresh-package",
        "internal-tool",
        "--force",
        "--reinstall",
        "internal-tool==1.2.3",
    ]


def test_python_tool_install_command_accepts_python() -> None:
    """Uv install commands should include a requested Python version."""
    assert uv_install_command("ruff==0.8.0", python="3.12") == [
        "uv",
        "tool",
        "install",
        "--python",
        "3.12",
        "ruff==0.8.0",
    ]


def test_python_tool_install_command_accepts_uv_config_file() -> None:
    """Uv install commands should include a requested uv config file."""
    assert uv_install_command("ruff==0.8.0", uv_config_file=Path("/prod/uv.toml")) == [
        "uv",
        "tool",
        "--config-file",
        "/prod/uv.toml",
        "install",
        "ruff==0.8.0",
    ]


def test_python_tool_install_command_accepts_uv_executable() -> None:
    """Uv install commands should use a requested uv executable path."""
    assert uv_install_command("ruff==0.8.0", uv_executable=Path("/opt/uv/bin/uv")) == [
        "/opt/uv/bin/uv",
        "tool",
        "install",
        "ruff==0.8.0",
    ]


def test_uv_compile_command_accepts_sources_and_config() -> None:
    """Uv compile commands should include resolver and config options."""
    assert uv_compile_command(
        Path("/prod/constraints.txt"),
        python="3.12",
        indexes=("https://packages.example/simple",),
        default_index="https://default.example/simple",
        find_links=("/prod/wheels",),
        no_index=True,
        index_strategy="unsafe-best-match",
        keyring_provider="subprocess",
        uv_config_file=Path("/prod/uv.toml"),
        uv_executable=Path("/opt/uv/bin/uv"),
    ) == [
        "/opt/uv/bin/uv",
        "--config-file",
        "/prod/uv.toml",
        "pip",
        "compile",
        "-",
        "--output-file",
        "/prod/constraints.txt",
        "--no-header",
        "--no-annotate",
        "--python",
        "3.12",
        "--index",
        "https://packages.example/simple",
        "--default-index",
        "https://default.example/simple",
        "--find-links",
        "/prod/wheels",
        "--no-index",
        "--index-strategy",
        "unsafe-best-match",
        "--keyring-provider",
        "subprocess",
    ]


def test_discover_url_requirements_extracts_uv_suggestions() -> None:
    """Uv URL dependency suggestions should be parsed from errors."""
    output = """
Package `url-dep` was included as a URL dependency. URL dependencies
must be expressed as direct requirements or constraints. Consider adding
`url-dep @ file:///tmp/url-dep` to your dependencies or constraints file.
""".strip()

    assert discover_url_requirements(output) == ("url-dep @ file:///tmp/url-dep",)


def test_generate_constraints_retries_discovered_url_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Constraint generation should retry with uv-suggested URL requirements.

    Args:
        tmp_path: Temporary deployment root.
        monkeypatch: Pytest helper used to replace process execution.
    """
    calls: list[tuple[list[str], str]] = []

    def fake_run(
        command: list[str],
        check: bool,
        input: str,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Fail once with a URL suggestion, then write constraints."""
        assert not check
        assert capture_output
        assert text
        calls.append((command, input))
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout="",
                stderr=("Consider adding `url-dep @ file:///tmp/url-dep` to your dependencies or constraints file."),
            )
        output_file = tmp_path / "constraints.txt"
        output_file.write_text("url-dep @ file:///tmp/url-dep\nurl-tool==1.0.0\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("module_manager.deploy.require_executable", lambda _name: "uv")
    monkeypatch.setattr("module_manager.deploy.subprocess.run", fake_run)

    result = generate_constraints(package="url-tool", output_file=tmp_path / "constraints.txt")

    assert result.output_file == tmp_path / "constraints.txt"
    assert result.requirements == ("url-tool", "url-dep @ file:///tmp/url-dep")
    assert result.discovered_url_dependencies == ("url-dep @ file:///tmp/url-dep",)
    assert result.iterations == 2
    assert calls[0][1] == "url-tool\n"
    assert calls[1][1] == "url-tool\nurl-dep @ file:///tmp/url-dep\n"
    assert (tmp_path / "constraints.txt").read_text(encoding="utf-8") == (
        "url-dep @ file:///tmp/url-dep\nurl-tool==1.0.0\n"
    )


def test_python_tool_install_command_accepts_url_dependency() -> None:
    """Uv install commands should pass direct URL dependencies unchanged."""
    package = "mytool @ https://packages.example/files/mytool-1.0.0-py3-none-any.whl"

    assert uv_install_command(package, constraints=("/prod/constraints.txt",)) == [
        "uv",
        "tool",
        "install",
        "--constraints",
        "/prod/constraints.txt",
        package,
    ]


def test_uv_install_environment_ignores_inherited_uv_tool_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Managed uv installs should ignore inherited tool-specific settings.

    Args:
        tmp_path: Temporary deployment root.
        monkeypatch: Pytest helper used to control the process environment.
    """
    monkeypatch.setenv("UV_TOOL_DIR", "/inherited/tools")
    monkeypatch.setenv("UV_TOOL_BIN_DIR", "/inherited/bin")
    monkeypatch.setenv("UV_TOOL_UPGRADE", "1")
    monkeypatch.setenv("UV_CONFIG_FILE", "/prod/uv.toml")

    env = uv_install_environment(tmp_path / "tools", tmp_path / "bin")

    assert env["UV_TOOL_DIR"] == str(tmp_path / "tools")
    assert env["UV_TOOL_BIN_DIR"] == str(tmp_path / "bin")
    assert "UV_TOOL_UPGRADE" not in env
    assert env["UV_CONFIG_FILE"] == "/prod/uv.toml"


def test_deploy_python_tool_writes_package_sources_to_install_hint(tmp_path: Path) -> None:
    """Generated module help should show the package source options.

    Args:
        tmp_path: Temporary deployment root.
    """
    paths = deploy_python_tool(
        name="internal-tool",
        version="1.2.3",
        package="internal-tool==1.2.3",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        indexes=("https://packages.example/simple",),
        default_index="https://default.example/simple",
        find_links=("/prod/wheels",),
        index_strategy="first-index",
        keyring_provider="disabled",
        constraints=("/prod/constraints.txt",),
        refresh_packages=("internal-tool",),
        force=True,
        uv_config_file=Path("/prod/uv.toml"),
    )

    modulefile = paths.modulefile.read_text(encoding="utf-8")
    assert "--config-file /prod/uv.toml" in modulefile
    assert "--index https://packages.example/simple" in modulefile
    assert "--default-index https://default.example/simple" in modulefile
    assert "--find-links /prod/wheels" in modulefile
    assert "--index-strategy first-index" in modulefile
    assert "--keyring-provider disabled" in modulefile
    assert "--constraints /prod/constraints.txt" in modulefile
    assert "--refresh-package internal-tool" in modulefile
    assert "--force" in modulefile


def test_deploy_python_tool_writes_url_dependency_to_install_hint(tmp_path: Path) -> None:
    """Generated module help should preserve direct URL package specs.

    Args:
        tmp_path: Temporary deployment root.
    """
    package = "mytool @ https://packages.example/files/mytool-1.0.0-py3-none-any.whl"
    paths = deploy_python_tool(
        name="mytool",
        version="1.0.0",
        package=package,
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        constraints=("/prod/constraints.txt",),
    )

    modulefile = paths.modulefile.read_text(encoding="utf-8")
    assert shlex_quote(package) in modulefile
    assert "--constraints /prod/constraints.txt" in modulefile


def test_require_executable_reports_missing_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing external commands should raise a clear deployment error.

    Args:
        monkeypatch: Pytest helper used to replace executable lookup.
    """
    monkeypatch.setattr("module_manager.deploy.shutil.which", lambda _name: None)

    with pytest.raises(MissingExecutableError, match="Required executable not found"):
        require_executable("uv")


def test_failed_python_install_rolls_back_new_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed Python installs should remove deployment paths created for the attempt.

    Args:
        tmp_path: Temporary deployment root.
        monkeypatch: Pytest helper used to replace process execution.
    """

    def fake_run(command: list[str], check: bool, env: dict[str, str]) -> None:
        """Simulate a failed uv install."""
        assert check
        assert env["UV_TOOL_BIN_DIR"]
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr("module_manager.deploy.require_executable", lambda _name: "uv")
    monkeypatch.setattr("module_manager.deploy.subprocess.run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        deploy_python_tool(
            name="ruff",
            version="0.8.0",
            package="ruff==0.8.0",
            module_root=tmp_path / "modules",
            prefix=tmp_path / "tools",
            execute_install=True,
        )

    assert not (tmp_path / "tools" / "ruff" / "0.8.0").exists()
    assert not (tmp_path / "modules" / "ruff" / "0.8.0").exists()


def test_deploy_rust_tool_copies_binary_and_marks_executable(tmp_path: Path) -> None:
    """Rust deployments should copy the binary and ensure it is executable.

    Args:
        tmp_path: Temporary deployment root.
    """
    binary = tmp_path / "rg"
    binary.write_text("binary", encoding="utf-8")

    paths = deploy_rust_tool(
        name="ripgrep",
        version="14.1.1",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        binary=binary,
    )

    deployed = paths.bin_dir / "ripgrep"
    assert deployed.exists()
    assert deployed.stat().st_mode & 0o111
    assert paths.modulefile.exists()


def test_deploy_rust_tool_dry_run_leaves_paths_unwritten(tmp_path: Path) -> None:
    """Dry-run Rust deployments should not write files.

    Args:
        tmp_path: Temporary deployment root.
    """
    binary = tmp_path / "rg"
    binary.write_text("binary", encoding="utf-8")

    paths = deploy_rust_tool(
        name="ripgrep",
        version="14.1.1",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        binary=binary,
        dry_run=True,
    )

    assert not paths.install_root.exists()
    assert not paths.modulefile.exists()


def test_deploy_script_tool_copies_script_and_marks_executable(tmp_path: Path) -> None:
    """Script deployments should copy the script and ensure it is executable.

    Args:
        tmp_path: Temporary deployment root.
    """
    script = tmp_path / "tool.sh"
    script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")

    paths = deploy_script_tool(
        name="tool",
        version="1.0.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        script=script,
    )

    deployed = paths.bin_dir / "tool"
    assert deployed.read_text(encoding="utf-8") == "#!/usr/bin/env bash\necho ok\n"
    assert deployed.stat().st_mode & 0o111
    assert "copy script to" in paths.modulefile.read_text(encoding="utf-8")


def test_deploy_script_tool_dry_run_leaves_paths_unwritten(tmp_path: Path) -> None:
    """Dry-run script deployments should not write files.

    Args:
        tmp_path: Temporary deployment root.
    """
    script = tmp_path / "tool.sh"
    script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")

    paths = deploy_script_tool(
        name="tool",
        version="1.0.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        script=script,
        dry_run=True,
    )

    assert not paths.install_root.exists()
    assert not paths.modulefile.exists()


def test_deploy_tool_can_skip_default_version(tmp_path: Path) -> None:
    """Deployments should leave the default-version file untouched when requested.

    Args:
        tmp_path: Temporary deployment root.
    """
    paths = deploy_rust_tool(
        name="ripgrep",
        version="14.1.1",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        make_default=False,
    )

    assert paths.default_version_file is not None
    assert not paths.default_version_file.exists()


def test_uninstall_tool_removes_install_modulefile_and_matching_default(tmp_path: Path) -> None:
    """Uninstall should remove a deployed version and its matching default.

    Args:
        tmp_path: Temporary deployment root.
    """
    paths = deploy_python_tool(
        name="ruff",
        version="0.8.0",
        package="ruff==0.8.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    result = uninstall_tool(
        name="ruff",
        version="0.8.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    assert paths.install_root in result.removed
    assert paths.modulefile in result.removed
    assert paths.default_version_file in result.removed
    assert result.default_version_removed
    assert not paths.install_root.exists()
    assert not paths.modulefile.exists()
    assert paths.default_version_file is not None
    assert not paths.default_version_file.exists()


def test_uninstall_tool_keeps_default_for_other_version(tmp_path: Path) -> None:
    """Uninstall should not remove a default selector for another version.

    Args:
        tmp_path: Temporary deployment root.
    """
    old_paths = deploy_python_tool(
        name="ruff",
        version="0.8.0",
        package="ruff==0.8.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )
    new_paths = deploy_python_tool(
        name="ruff",
        version="0.9.0",
        package="ruff==0.9.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    result = uninstall_tool(
        name="ruff",
        version="0.8.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    assert old_paths.install_root in result.removed
    assert not result.default_version_removed
    assert new_paths.default_version_file is not None
    assert new_paths.default_version_file.exists()
    assert is_default_version(new_paths.default_version_file.read_text(encoding="utf-8"), "0.9.0")


def test_uninstall_tool_dry_run_leaves_paths_in_place(tmp_path: Path) -> None:
    """Dry-run uninstall should report targets without deleting them.

    Args:
        tmp_path: Temporary deployment root.
    """
    paths = deploy_rust_tool(
        name="ripgrep",
        version="14.1.1",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    result = uninstall_tool(
        name="ripgrep",
        version="14.1.1",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        dry_run=True,
    )

    assert paths.install_root in result.removed
    assert paths.modulefile in result.removed
    assert paths.install_root.exists()
    assert paths.modulefile.exists()


def test_load_environment_spec_reads_manifest(tmp_path: Path) -> None:
    """Environment manifests should parse deploy-equivalent tool options.

    Args:
        tmp_path: Temporary manifest root.
    """
    manifest = tmp_path / "env.toml"
    manifest.write_text(
        """
name = "dev-tools"
version = "2026.05"
prefix = "/prod/tools"
module_root = "/prod/modulefiles"
default = false

[[tools]]
type = "python"
name = "ruff"
version = "0.8.0"
package = "ruff==0.8.0"
python = "3.12"
indexes = ["https://packages.example/simple"]
default_index = "https://default.example/simple"
find_links = ["/prod/wheels"]
no_index = true
index_strategy = "unsafe-best-match"
keyring_provider = "subprocess"
constraints = ["constraints.txt", "/prod/global-constraints.txt"]
no_cache = true
refresh = true
refresh_packages = ["ruff"]
force = true
reinstall = true
uv_config_file = "uv.toml"
uv_executable = "bin/uv"

[[tools]]
type = "script"
name = "helper"
script = "scripts/helper"
""".strip(),
        encoding="utf-8",
    )

    spec = load_environment_spec(manifest)

    assert spec.name == "dev-tools"
    assert spec.version == "2026.05"
    assert spec.prefix == Path("/prod/tools")
    assert spec.module_root == Path("/prod/modulefiles")
    assert not spec.make_default
    assert spec.tools[0].package == "ruff==0.8.0"
    assert spec.tools[0].indexes == ("https://packages.example/simple",)
    assert spec.tools[0].default_index == "https://default.example/simple"
    assert spec.tools[0].no_index
    assert spec.tools[0].index_strategy == "unsafe-best-match"
    assert spec.tools[0].keyring_provider == "subprocess"
    assert spec.tools[0].constraints == (str(tmp_path / "constraints.txt"), "/prod/global-constraints.txt")
    assert spec.tools[0].no_cache
    assert spec.tools[0].refresh
    assert spec.tools[0].refresh_packages == ("ruff",)
    assert spec.tools[0].force
    assert spec.tools[0].reinstall
    assert spec.tools[0].uv_config_file == tmp_path / "uv.toml"
    assert spec.tools[0].uv_executable == tmp_path / "bin/uv"
    assert spec.tools[1].script == tmp_path / "scripts/helper"


def test_load_environment_spec_rejects_invalid_tool_entries(tmp_path: Path) -> None:
    """Environment manifests should reject invalid tool tables.

    Args:
        tmp_path: Temporary manifest root.
    """
    cases = [
        ("tools = []", "tools must contain at least one entry"),
        ('name = "x"\nversion = "1"\ntools = ["bad"]', "tools\\[1\\] must be a TOML table"),
        (
            'name = "x"\nversion = "1"\n[[tools]]\ntype = "python"\nname = "ruff"',
            "package is required",
        ),
        (
            'name = "x"\nversion = "1"\n[[tools]]\ntype = "rust"\nname = "rg"',
            "binary is required",
        ),
        (
            'name = "x"\nversion = "1"\n[[tools]]\ntype = "script"\nname = "helper"',
            "script is required",
        ),
        (
            'name = "x"\nversion = "1"\n[[tools]]\ntype = "other"\nname = "tool"',
            "type must be one of",
        ),
        (
            (
                'name = "x"\nversion = "1"\n[[tools]]\ntype = "python"\n'
                'name = "ruff"\npackage = "ruff"\nindex_strategy = "bad"'
            ),
            "index_strategy must be one of",
        ),
        (
            (
                'name = "x"\nversion = "1"\n[[tools]]\ntype = "python"\n'
                'name = "ruff"\npackage = "ruff"\nkeyring_provider = "bad"'
            ),
            "keyring_provider must be one of",
        ),
    ]

    for index, (content, message) in enumerate(cases):
        manifest = tmp_path / f"env-{index}.toml"
        manifest.write_text(content, encoding="utf-8")
        with pytest.raises(TypeError, match=message):
            load_environment_spec(manifest)


def test_deploy_environment_writes_shared_module(tmp_path: Path) -> None:
    """Collective environments should expose all copied tools from one module.

    Args:
        tmp_path: Temporary deployment root.
    """
    binary = tmp_path / "rg"
    script = tmp_path / "helper"
    manifest = tmp_path / "env.toml"
    binary.write_text("binary", encoding="utf-8")
    script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    manifest.write_text(
        f"""
name = "dev-tools"
version = "2026.05"

[[tools]]
type = "rust"
name = "ripgrep"
binary = "{binary}"

[[tools]]
type = "script"
name = "helper"
script = "{script}"
""".strip(),
        encoding="utf-8",
    )
    spec = load_environment_spec(manifest)

    result = deploy_environment(
        spec=spec,
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    assert (result.paths.bin_dir / "ripgrep").exists()
    assert (result.paths.bin_dir / "helper").exists()
    assert result.paths.modulefile.exists()
    assert result.paths.default_version_file is not None
    assert result.paths.default_version_file.exists()


def test_deploy_environment_installs_python_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Collective environments should install Python entries with uv.

    Args:
        tmp_path: Temporary deployment root.
        monkeypatch: Pytest helper used to replace process execution.
    """
    calls: list[tuple[list[str], dict[str, str]]] = []
    executable_checks: list[str] = []

    def fake_run(command: list[str], check: bool, env: dict[str, str]) -> None:
        """Record the subprocess call made by deployment."""
        assert check
        calls.append((command, env))

    def fake_require_executable(name: str) -> str:
        """Record executable availability checks."""
        executable_checks.append(name)
        return name

    monkeypatch.setattr("module_manager.deploy.require_executable", fake_require_executable)
    monkeypatch.setattr("module_manager.deploy.subprocess.run", fake_run)
    manifest = tmp_path / "env.toml"
    manifest.write_text(
        """
name = "dev-tools"
version = "2026.05"

[[tools]]
type = "python"
name = "ruff"
package = "ruff==0.8.0"
python = "3.12"
default_index = "https://default.example/simple"
no_index = true
constraints = ["constraints.txt"]
no_cache = true
refresh = true
refresh_packages = ["ruff"]
force = true
uv_config_file = "uv.toml"
""".strip(),
        encoding="utf-8",
    )
    spec = load_environment_spec(manifest)

    result = deploy_environment(
        spec=spec,
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        uv_executable=tmp_path / "custom-uv",
    )

    assert calls[0][0] == [
        str(tmp_path / "custom-uv"),
        "tool",
        "--config-file",
        str(tmp_path / "uv.toml"),
        "install",
        "--python",
        "3.12",
        "--default-index",
        "https://default.example/simple",
        "--no-index",
        "--constraints",
        str(tmp_path / "constraints.txt"),
        "--no-cache",
        "--refresh",
        "--refresh-package",
        "ruff",
        "--force",
        "ruff==0.8.0",
    ]
    assert executable_checks == [str(tmp_path / "custom-uv")]
    assert calls[0][1]["UV_TOOL_DIR"] == str(result.paths.install_root / "uv-tools")
    assert calls[0][1]["UV_TOOL_BIN_DIR"] == str(result.paths.bin_dir)
    assert result.paths.modulefile.exists()


def test_deploy_environment_dry_run_leaves_paths_unwritten(tmp_path: Path) -> None:
    """Dry-run collective environments should report actions without writes.

    Args:
        tmp_path: Temporary deployment root.
    """
    manifest = tmp_path / "env.toml"
    manifest.write_text(
        """
name = "dev-tools"
version = "2026.05"

[[tools]]
type = "python"
name = "ruff"
package = "ruff==0.8.0"
""".strip(),
        encoding="utf-8",
    )
    spec = load_environment_spec(manifest)

    result = deploy_environment(
        spec=spec,
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
        dry_run=True,
    )

    assert any(action.startswith("install python ruff:") for action in result.actions)
    assert not result.paths.install_root.exists()
    assert not result.paths.modulefile.exists()
