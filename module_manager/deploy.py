"""Deployment routines for Python and Rust command-line tools."""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .modulefile import ModuleSpec, render_modulefile


class MissingExecutableError(RuntimeError):
    """Raised when a required external executable is unavailable."""


@dataclass(frozen=True)
class DeploymentPaths:
    """Filesystem paths created or targeted by a deployment."""

    install_root: Path
    bin_dir: Path
    modulefile: Path


def deployment_paths(module_root: Path, prefix: Path, name: str, version: str) -> DeploymentPaths:
    """Compute versioned installation and modulefile paths for a tool."""
    install_root = prefix / name / version
    return DeploymentPaths(
        install_root=install_root,
        bin_dir=install_root / "bin",
        modulefile=module_root / name / version,
    )


def uv_install_command(
    package: str,
    python: str | None = None,
    indexes: tuple[str, ...] = (),
    find_links: tuple[str, ...] = (),
) -> list[str]:
    """Build the uv command used to install a Python CLI tool."""
    command = ["uv", "tool", "install"]
    if python:
        command.extend(["--python", python])
    for index in indexes:
        command.extend(["--index", index])
    for link in find_links:
        command.extend(["--find-links", link])
    command.append(package)
    return command


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text to a path, creating parent directories first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def require_executable(name: str) -> str:
    """Return an executable path or raise a clear runtime error."""
    executable = shutil.which(name)
    if executable is None:
        msg = f"Required executable not found on PATH: {name}"
        raise MissingExecutableError(msg)
    return executable


def deploy_python_tool(
    *,
    name: str,
    version: str,
    package: str,
    module_root: Path,
    prefix: Path,
    description: str | None = None,
    homepage: str | None = None,
    python: str | None = None,
    indexes: tuple[str, ...] = (),
    find_links: tuple[str, ...] = (),
    execute_install: bool = False,
) -> DeploymentPaths:
    """Deploy metadata for a Python tool and optionally install it with uv."""
    paths = deployment_paths(module_root, prefix, name, version)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    tool_dir = paths.install_root / "uv-tools"
    command = uv_install_command(package, python, indexes, find_links)

    if execute_install:
        require_executable("uv")
        env = os.environ.copy()
        env["UV_TOOL_DIR"] = str(tool_dir)
        env["UV_TOOL_BIN_DIR"] = str(paths.bin_dir)
        subprocess.run(command, check=True, env=env)

    install_hint = (
        f"UV_TOOL_DIR={shlex.quote(str(tool_dir))} "
        f"UV_TOOL_BIN_DIR={shlex.quote(str(paths.bin_dir))} "
        f"{shlex.join(command)}"
    )
    modulefile = render_modulefile(
        ModuleSpec(
            name=name,
            version=version,
            root=paths.install_root,
            bin_dir=paths.bin_dir,
            description=description,
            homepage=homepage,
            install_hint=install_hint,
        )
    )
    write_text(paths.modulefile, modulefile)
    return paths


def deploy_rust_tool(
    *,
    name: str,
    version: str,
    module_root: Path,
    prefix: Path,
    binary: Path | None = None,
    description: str | None = None,
    homepage: str | None = None,
) -> DeploymentPaths:
    """Deploy metadata for a Rust tool and optionally copy its binary."""
    paths = deployment_paths(module_root, prefix, name, version)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)

    if binary:
        target = paths.bin_dir / name
        shutil.copy2(binary, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    modulefile = render_modulefile(
        ModuleSpec(
            name=name,
            version=version,
            root=paths.install_root,
            bin_dir=paths.bin_dir,
            description=description,
            homepage=homepage,
            install_hint=f"copy binary to {paths.bin_dir / name}",
        )
    )
    write_text(paths.modulefile, modulefile)
    return paths
