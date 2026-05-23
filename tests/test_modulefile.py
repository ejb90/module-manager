"""Modulefile rendering and deployment helper tests."""

from pathlib import Path

import pytest

from module_manager.deploy import (
    MissingExecutableError,
    deploy_python_tool,
    deploy_rust_tool,
    deploy_script_tool,
    require_executable,
    uninstall_tool,
    uv_install_command,
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
        find_links=("/prod/wheels",),
    ) == [
        "uv",
        "tool",
        "install",
        "--index",
        "https://packages.example/simple",
        "--index",
        "https://mirror.example/simple",
        "--find-links",
        "/prod/wheels",
        "internal-tool==1.2.3",
    ]


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
        find_links=("/prod/wheels",),
    )

    modulefile = paths.modulefile.read_text(encoding="utf-8")
    assert "--index https://packages.example/simple" in modulefile
    assert "--find-links /prod/wheels" in modulefile


def test_require_executable_reports_missing_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing external commands should raise a clear deployment error.

    Args:
        monkeypatch: Pytest helper used to replace executable lookup.
    """
    monkeypatch.setattr("module_manager.deploy.shutil.which", lambda _name: None)

    with pytest.raises(MissingExecutableError, match="Required executable not found"):
        require_executable("uv")


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
