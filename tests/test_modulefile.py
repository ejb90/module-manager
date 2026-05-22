"""Modulefile rendering and deployment helper tests."""

from pathlib import Path

import pytest

from module_manager.deploy import (
    MissingExecutableError,
    deploy_python_tool,
    deploy_rust_tool,
    require_executable,
    uv_install_command,
)
from module_manager.modulefile import ModuleSpec, render_modulefile, tcl_quote


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


def test_deploy_python_tool_writes_modulefile(tmp_path: Path) -> None:
    """Python deployments should create the bin directory and modulefile."""
    paths = deploy_python_tool(
        name="ruff",
        version="0.8.0",
        package="ruff==0.8.0",
        module_root=tmp_path / "modules",
        prefix=tmp_path / "tools",
    )

    assert paths.modulefile.exists()
    assert paths.bin_dir.is_dir()
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
    """Generated module help should show the package source options."""
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
    """Missing external commands should raise a clear deployment error."""
    monkeypatch.setattr("module_manager.deploy.shutil.which", lambda _name: None)

    with pytest.raises(MissingExecutableError, match="Required executable not found"):
        require_executable("uv")


def test_deploy_rust_tool_copies_binary_and_marks_executable(tmp_path: Path) -> None:
    """Rust deployments should copy the binary and ensure it is executable."""
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
