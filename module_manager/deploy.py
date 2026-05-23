"""Deployment routines for Python, Rust, and shell command-line tools."""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .modulefile import ModuleSpec, is_default_version, render_default_version, render_modulefile


class MissingExecutableError(RuntimeError):
    """Raised when a required external executable is unavailable."""


@dataclass(frozen=True)
class DeploymentPaths:
    """Filesystem paths created or targeted by a deployment.

    Attributes:
        install_root: Versioned installation root for a tool.
        bin_dir: Executable directory exposed by the modulefile.
        modulefile: Versioned modulefile path.
        default_version_file: Optional `.version` selector path for the tool.
    """

    install_root: Path
    bin_dir: Path
    modulefile: Path
    default_version_file: Path | None = None


@dataclass(frozen=True)
class UninstallResult:
    """Filesystem paths removed or left behind by an uninstall.

    Attributes:
        paths: Canonical deployment paths for the requested tool version.
        removed: Paths removed, or paths that would be removed during a dry run.
        default_version_removed: Whether the default selector matched the
            uninstalled version.
    """

    paths: DeploymentPaths
    removed: tuple[Path, ...]
    default_version_removed: bool


def deployment_paths(module_root: Path, prefix: Path, name: str, version: str) -> DeploymentPaths:
    """Compute versioned installation and modulefile paths for a tool.

    Args:
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        name: Tool name.
        version: Tool version.

    Returns:
        Paths used by deploy and uninstall operations.
    """
    install_root = prefix / name / version
    return DeploymentPaths(
        install_root=install_root,
        bin_dir=install_root / "bin",
        modulefile=module_root / name / version,
        default_version_file=module_root / name / ".version",
    )


def uv_install_command(
    package: str,
    python: str | None = None,
    indexes: tuple[str, ...] = (),
    find_links: tuple[str, ...] = (),
) -> list[str]:
    """Build the uv command used to install a Python CLI tool.

    Args:
        package: Package spec passed to `uv tool install`.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs.
        find_links: Wheelhouse directories or HTML package pages.

    Returns:
        Tokenized uv command suitable for `subprocess.run`.
    """
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
    """Write UTF-8 text to a path, creating parent directories first.

    Args:
        path: Destination file path.
        content: Text content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def require_executable(name: str) -> str:
    """Return an executable path or raise a clear runtime error.

    Args:
        name: Executable name to find on `PATH`.

    Returns:
        Absolute path returned by `shutil.which`.

    Raises:
        MissingExecutableError: If the executable cannot be found.
    """
    executable = shutil.which(name)
    if executable is None:
        msg = f"Required executable not found on PATH: {name}"
        raise MissingExecutableError(msg)
    return executable


def write_default_version(paths: DeploymentPaths, version: str, make_default: bool) -> None:
    """Write the default-version file when requested.

    Args:
        paths: Deployment paths containing the default selector location.
        version: Version to select as the default.
        make_default: Whether to write the selector file.
    """
    if make_default and paths.default_version_file:
        write_text(paths.default_version_file, render_default_version(version))


def prune_empty_dir(path: Path, stop: Path) -> None:
    """Remove empty parent directories up to, but not including, a stop path.

    Args:
        path: First directory to remove if it is empty.
        stop: Ancestor directory where pruning must stop.
    """
    current = path
    while current != stop and stop in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def remove_path(path: Path) -> bool:
    """Remove one filesystem path when it exists.

    Args:
        path: File, symlink, or directory to remove.

    Returns:
        `True` when a path was removed, otherwise `False`.
    """
    if path.is_symlink() or path.is_file():
        path.unlink()
        return True
    if path.is_dir():
        shutil.rmtree(path)
        return True
    return False


def uninstall_tool(
    *,
    name: str,
    version: str,
    module_root: Path,
    prefix: Path,
    remove_default: bool = True,
    dry_run: bool = False,
) -> UninstallResult:
    """Remove a deployed tool version and its matching modulefile.

    Args:
        name: Tool name.
        version: Tool version to remove.
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        remove_default: Whether to remove a matching default selector.
        dry_run: Whether to report paths without deleting them.

    Returns:
        Summary of paths removed, or paths that would be removed during a dry
        run.
    """
    paths = deployment_paths(module_root, prefix, name, version)
    targets = (paths.install_root, paths.modulefile)
    removed: list[Path] = []

    for target in targets:
        if target.exists() or target.is_symlink():
            removed.append(target)
            if not dry_run:
                remove_path(target)

    default_removed = False
    if remove_default and paths.default_version_file and paths.default_version_file.exists():
        default_content = paths.default_version_file.read_text(encoding="utf-8")
        if is_default_version(default_content, version):
            default_removed = True
            removed.append(paths.default_version_file)
            if not dry_run:
                paths.default_version_file.unlink()

    if not dry_run:
        prune_empty_dir(paths.modulefile.parent, module_root)
        prune_empty_dir(paths.install_root.parent, prefix)

    return UninstallResult(paths=paths, removed=tuple(removed), default_version_removed=default_removed)


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
    make_default: bool = True,
) -> DeploymentPaths:
    """Deploy metadata for a Python tool and optionally install it with uv.

    Args:
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        package: Package spec passed to `uv tool install`.
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        execute_install: Whether to run `uv tool install` immediately.
        make_default: Whether to make this version the module default.

    Returns:
        Paths created or targeted by the deployment.

    Raises:
        MissingExecutableError: If `execute_install` is true and uv is not on
            `PATH`.
        subprocess.CalledProcessError: If `uv tool install` fails.
    """
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
    write_default_version(paths, version, make_default)
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
    make_default: bool = True,
) -> DeploymentPaths:
    """Deploy metadata for a Rust tool and optionally copy its binary.

    Args:
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        binary: Optional compiled binary to copy into the deployed `bin`
            directory.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        make_default: Whether to make this version the module default.

    Returns:
        Paths created or targeted by the deployment.
    """
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
    write_default_version(paths, version, make_default)
    return paths


def deploy_script_tool(
    *,
    name: str,
    version: str,
    module_root: Path,
    prefix: Path,
    script: Path | None = None,
    description: str | None = None,
    homepage: str | None = None,
    make_default: bool = True,
) -> DeploymentPaths:
    """Deploy metadata for a shell script and optionally copy it into `bin`.

    Args:
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        script: Optional shell script to copy into the deployed `bin` directory.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        make_default: Whether to make this version the module default.

    Returns:
        Paths created or targeted by the deployment.
    """
    paths = deployment_paths(module_root, prefix, name, version)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)

    if script:
        target = paths.bin_dir / name
        shutil.copy2(script, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    modulefile = render_modulefile(
        ModuleSpec(
            name=name,
            version=version,
            root=paths.install_root,
            bin_dir=paths.bin_dir,
            description=description,
            homepage=homepage,
            install_hint=f"copy script to {paths.bin_dir / name}",
        )
    )
    write_text(paths.modulefile, modulefile)
    write_default_version(paths, version, make_default)
    return paths
