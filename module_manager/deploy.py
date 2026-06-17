"""Deployment routines for Python, Rust, and shell command-line tools."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import stat
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .modulefile import ModuleSpec, is_default_version, render_default_version, render_modulefile


class MissingExecutableError(RuntimeError):
    """Raised when a required external executable is unavailable."""


class ConstraintGenerationError(RuntimeError):
    """Raised when uv cannot generate constraints after URL discovery."""


VALID_INDEX_STRATEGIES = ("first-index", "unsafe-first-match", "unsafe-best-match")
VALID_KEYRING_PROVIDERS = ("disabled", "subprocess")


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


@dataclass(frozen=True)
class EnvironmentToolSpec:
    """One tool entry in a collective environment manifest.

    Attributes:
        tool_type: Tool backend, such as `python`, `rust`, or `script`.
        name: Tool name used for copied binaries and reporting.
        version: Optional source tool version for documentation.
        package: Python package spec passed to `uv tool install`.
        uv_config_file: uv configuration file passed to `uv tool`.
        uv_executable: uv executable path.
        binary: Rust binary path to copy into the shared `bin` directory.
        script: Shell script path to copy into the shared `bin` directory.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs passed to uv.
        default_index: Default package index URL passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        no_index: Whether uv should ignore registry indexes.
        index_strategy: Package index strategy passed to uv.
        keyring_provider: Keyring provider passed to uv.
        constraints: Constraint requirement files passed to uv.
        no_cache: Whether uv should avoid reading from or writing to cache.
        refresh: Whether uv should refresh cached data.
        refresh_packages: Packages whose cached data uv should refresh.
        force: Whether uv should replace existing executable entries.
        reinstall: Whether uv should reinstall all packages.
        description: Optional tool description.
        homepage: Optional upstream homepage.
    """

    tool_type: str
    name: str
    version: str | None = None
    package: str | None = None
    uv_config_file: Path | None = None
    uv_executable: Path | None = None
    binary: Path | None = None
    script: Path | None = None
    python: str | None = None
    indexes: tuple[str, ...] = ()
    default_index: str | None = None
    find_links: tuple[str, ...] = ()
    no_index: bool = False
    index_strategy: str | None = None
    keyring_provider: str | None = None
    constraints: tuple[str, ...] = ()
    no_cache: bool = False
    refresh: bool = False
    refresh_packages: tuple[str, ...] = ()
    force: bool = False
    reinstall: bool = False
    description: str | None = None
    homepage: str | None = None


@dataclass(frozen=True)
class EnvironmentSpec:
    """Collective environment deployment specification.

    Attributes:
        name: Environment module name.
        version: Environment module version.
        tools: Tool entries to install or copy into the shared environment.
        prefix: Optional install prefix from the manifest.
        module_root: Optional module tree root from the manifest.
        description: Optional environment module description.
        homepage: Optional homepage shown in module help.
        make_default: Whether to make this environment version the default.
    """

    name: str
    version: str
    tools: tuple[EnvironmentToolSpec, ...]
    prefix: Path | None = None
    module_root: Path | None = None
    description: str | None = None
    homepage: str | None = None
    make_default: bool = True


@dataclass(frozen=True)
class EnvironmentDeploymentResult:
    """Result of deploying or previewing a collective environment.

    Attributes:
        paths: Filesystem paths for the collective environment.
        actions: Human-readable actions performed, or planned during dry runs.
    """

    paths: DeploymentPaths
    actions: tuple[str, ...]


@dataclass(frozen=True)
class ConstraintGenerationResult:
    """Result of generating a Python constraints file.

    Attributes:
        output_file: Constraints file written by uv.
        requirements: Initial and discovered direct requirements compiled.
        discovered_url_dependencies: URL requirements discovered from uv errors.
        iterations: Number of uv compile attempts.
    """

    output_file: Path
    requirements: tuple[str, ...]
    discovered_url_dependencies: tuple[str, ...]
    iterations: int


URL_DEPENDENCY_RE = re.compile(r"`([^`]+?\s@\s[^`]+?)`")


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
    default_index: str | None = None,
    find_links: tuple[str, ...] = (),
    no_index: bool = False,
    index_strategy: str | None = None,
    keyring_provider: str | None = None,
    constraints: tuple[str, ...] = (),
    no_cache: bool = False,
    refresh: bool = False,
    refresh_packages: tuple[str, ...] = (),
    force: bool = False,
    reinstall: bool = False,
    uv_config_file: Path | None = None,
    uv_executable: Path | None = None,
) -> list[str]:
    """Build the uv command used to install a Python CLI tool.

    Args:
        package: Package spec passed to `uv tool install`.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs.
        default_index: Default package index URL.
        find_links: Wheelhouse directories or HTML package pages.
        no_index: Whether to ignore registry indexes.
        index_strategy: Package index strategy.
        keyring_provider: Keyring provider.
        constraints: Constraint requirement files.
        no_cache: Whether to avoid reading from or writing to cache.
        refresh: Whether to refresh cached data.
        refresh_packages: Packages whose cached data uv should refresh.
        force: Whether to replace existing executable entries.
        reinstall: Whether to reinstall all packages.
        uv_config_file: Optional uv configuration file passed to `uv tool`.
        uv_executable: Optional uv executable path.

    Returns:
        Tokenized uv command suitable for `subprocess.run`.
    """
    command = [str(uv_executable or "uv"), "tool"]
    if uv_config_file:
        command.extend(["--config-file", str(uv_config_file)])
    command.append("install")
    if python:
        command.extend(["--python", python])
    for index in indexes:
        command.extend(["--index", index])
    if default_index:
        command.extend(["--default-index", default_index])
    for link in find_links:
        command.extend(["--find-links", link])
    if no_index:
        command.append("--no-index")
    if index_strategy:
        command.extend(["--index-strategy", index_strategy])
    if keyring_provider:
        command.extend(["--keyring-provider", keyring_provider])
    for constraint in constraints:
        command.extend(["--constraints", constraint])
    if no_cache:
        command.append("--no-cache")
    if refresh:
        command.append("--refresh")
    for package_name in refresh_packages:
        command.extend(["--refresh-package", package_name])
    if force:
        command.append("--force")
    if reinstall:
        command.append("--reinstall")
    command.append(package)
    return command


def uv_compile_command(
    output_file: Path,
    python: str | None = None,
    indexes: tuple[str, ...] = (),
    default_index: str | None = None,
    find_links: tuple[str, ...] = (),
    no_index: bool = False,
    index_strategy: str | None = None,
    keyring_provider: str | None = None,
    uv_config_file: Path | None = None,
    uv_executable: Path | None = None,
) -> list[str]:
    """Build the uv command used to compile Python constraints.

    Args:
        output_file: Destination constraints file.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs.
        default_index: Default package index URL.
        find_links: Wheelhouse directories or HTML package pages.
        no_index: Whether to ignore registry indexes.
        index_strategy: Package index strategy.
        keyring_provider: Keyring provider.
        uv_config_file: Optional uv configuration file passed to `uv`.
        uv_executable: Optional uv executable path.

    Returns:
        Tokenized uv command suitable for `subprocess.run`.
    """
    command = [str(uv_executable or "uv")]
    if uv_config_file:
        command.extend(["--config-file", str(uv_config_file)])
    command.extend(
        [
            "pip",
            "compile",
            "-",
            "--output-file",
            str(output_file),
            "--no-header",
            "--no-annotate",
        ]
    )
    if python:
        command.extend(["--python", python])
    for index in indexes:
        command.extend(["--index", index])
    if default_index:
        command.extend(["--default-index", default_index])
    for link in find_links:
        command.extend(["--find-links", link])
    if no_index:
        command.append("--no-index")
    if index_strategy:
        command.extend(["--index-strategy", index_strategy])
    if keyring_provider:
        command.extend(["--keyring-provider", keyring_provider])
    return command


def discover_url_requirements(output: str) -> tuple[str, ...]:
    """Extract uv-suggested direct URL requirements from compiler output.

    Args:
        output: Combined stdout and stderr from `uv pip compile`.

    Returns:
        Direct URL requirements in discovery order.
    """
    requirements: list[str] = []
    for match in URL_DEPENDENCY_RE.findall(output):
        if match not in requirements:
            requirements.append(match)
    return tuple(requirements)


def generate_constraints(
    *,
    package: str,
    output_file: Path,
    python: str | None = None,
    indexes: tuple[str, ...] = (),
    default_index: str | None = None,
    find_links: tuple[str, ...] = (),
    no_index: bool = False,
    index_strategy: str | None = None,
    keyring_provider: str | None = None,
    uv_config_file: Path | None = None,
    uv_executable: Path | None = None,
    max_iterations: int = 20,
) -> ConstraintGenerationResult:
    """Generate a constraints file, discovering transitive URL dependencies.

    Args:
        package: Initial package requirement to compile.
        output_file: Destination constraints file.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs passed to uv.
        default_index: Default package index URL passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        no_index: Whether uv should ignore registry indexes.
        index_strategy: Package index strategy passed to uv.
        keyring_provider: Keyring provider passed to uv.
        uv_config_file: Optional uv configuration file passed to `uv`.
        uv_executable: Optional uv executable path.
        max_iterations: Maximum uv compile attempts before failing.

    Returns:
        Constraints generation result.

    Raises:
        MissingExecutableError: If uv is not on `PATH`.
        ConstraintGenerationError: If uv fails without a new URL dependency to
            add, or if the iteration limit is reached.
    """
    require_executable(str(uv_executable or "uv"))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    requirements = [package]
    discovered: list[str] = []
    command = uv_compile_command(
        output_file,
        python,
        indexes,
        default_index,
        find_links,
        no_index,
        index_strategy,
        keyring_provider,
        uv_config_file,
        uv_executable,
    )

    for iteration in range(1, max_iterations + 1):
        completed = subprocess.run(
            command,
            check=False,
            input="\n".join(requirements) + "\n",
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return ConstraintGenerationResult(
                output_file=output_file,
                requirements=tuple(requirements),
                discovered_url_dependencies=tuple(discovered),
                iterations=iteration,
            )

        combined_output = f"{completed.stdout}\n{completed.stderr}"
        new_requirements = [
            requirement for requirement in discover_url_requirements(combined_output) if requirement not in requirements
        ]
        if not new_requirements:
            msg = combined_output.strip() or f"uv pip compile failed with exit code {completed.returncode}"
            raise ConstraintGenerationError(msg)
        requirements.extend(new_requirements)
        discovered.extend(new_requirements)

    msg = f"uv pip compile did not converge after {max_iterations} attempts"
    raise ConstraintGenerationError(msg)


def uv_install_environment(tool_dir: Path, bin_dir: Path) -> dict[str, str]:
    """Build an isolated environment for a managed uv tool installation.

    Args:
        tool_dir: Directory where uv should store installed tools.
        bin_dir: Directory where uv should install tool executables.

    Returns:
        Process environment with inherited `UV_TOOL_*` settings removed and
        the managed tool destinations set.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("UV_TOOL_")}
    env["UV_TOOL_DIR"] = str(tool_dir)
    env["UV_TOOL_BIN_DIR"] = str(bin_dir)
    return env


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


def copy_executable(source: Path, target: Path, dry_run: bool = False) -> None:
    """Copy a file and mark it executable unless this is a dry run.

    Args:
        source: Existing source file to copy.
        target: Destination executable path.
        dry_run: Whether to skip filesystem mutation.
    """
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


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


def rollback_deployment(paths: DeploymentPaths, install_root_existed: bool, modulefile_existed: bool) -> None:
    """Remove paths created by a failed deployment attempt.

    Args:
        paths: Deployment paths targeted by the failed operation.
        install_root_existed: Whether the install root predated the attempt.
        modulefile_existed: Whether the modulefile predated the attempt.
    """
    if not modulefile_existed:
        remove_path(paths.modulefile)
    if not install_root_existed:
        remove_path(paths.install_root)


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


def require_string(data: dict[str, Any], key: str) -> str:
    """Read a required string from manifest data.

    Args:
        data: Manifest table.
        key: Required key.

    Returns:
        Configured string value.

    Raises:
        TypeError: If the value is missing or not a string.
    """
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    msg = f"{key} must be a non-empty string"
    raise TypeError(msg)


def optional_string(data: dict[str, Any], key: str) -> str | None:
    """Read an optional string from manifest data.

    Args:
        data: Manifest table.
        key: Optional key.

    Returns:
        Configured string value, or `None`.

    Raises:
        TypeError: If the value is not a string.
    """
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    msg = f"{key} must be a string"
    raise TypeError(msg)


def optional_manifest_path(data: dict[str, Any], key: str, base_dir: Path | None = None) -> Path | None:
    """Read an optional path from manifest data.

    Args:
        data: Manifest table.
        key: Optional path key.
        base_dir: Directory used to resolve relative paths.

    Returns:
        Expanded path value, or `None`.

    Raises:
        TypeError: If the value is not a string.
    """
    value = optional_string(data, key)
    if value is None:
        return None
    path = Path(value).expanduser()
    if base_dir and not path.is_absolute():
        return base_dir / path
    return path


def optional_manifest_paths(data: dict[str, Any], key: str, base_dir: Path | None = None) -> tuple[Path, ...]:
    """Read optional paths from manifest data.

    Args:
        data: Manifest table.
        key: Optional path-list key.
        base_dir: Directory used to resolve relative paths.

    Returns:
        Expanded path values, or an empty tuple.

    Raises:
        TypeError: If the value is not a list of strings.
    """
    paths = []
    for value in optional_string_tuple(data, key):
        path = Path(value).expanduser()
        if base_dir and not path.is_absolute():
            path = base_dir / path
        paths.append(path)
    return tuple(paths)


def optional_string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    """Read an optional list of strings from manifest data.

    Args:
        data: Manifest table.
        key: Optional list key.

    Returns:
        Configured strings, or an empty tuple.

    Raises:
        TypeError: If the value is not a list of strings.
    """
    value = data.get(key)
    if value is None:
        return ()
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    msg = f"{key} must be a list of strings"
    raise TypeError(msg)


def optional_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    """Read an optional boolean from manifest data.

    Args:
        data: Manifest table.
        key: Optional boolean key.
        default: Value to use when the key is absent.

    Returns:
        Configured boolean value or the default.

    Raises:
        TypeError: If the value is not a boolean.
    """
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    msg = f"{key} must be a boolean"
    raise TypeError(msg)


def load_environment_spec(path: Path) -> EnvironmentSpec:
    """Load a collective environment specification from TOML.

    Args:
        path: TOML manifest path.

    Returns:
        Parsed environment specification.

    Raises:
        TypeError: If a manifest value has the wrong type.
        tomllib.TOMLDecodeError: If the manifest is not valid TOML.
    """
    manifest_path = path.expanduser()
    base_dir = manifest_path.parent
    data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    raw_tools = data.get("tools")
    if not isinstance(raw_tools, list):
        msg = "tools must be a list of tables"
        raise TypeError(msg)

    tools = tuple(parse_environment_tool(item, base_dir, index) for index, item in enumerate(raw_tools, start=1))
    if not tools:
        msg = "tools must contain at least one entry"
        raise TypeError(msg)

    return EnvironmentSpec(
        name=require_string(data, "name"),
        version=require_string(data, "version"),
        tools=tools,
        prefix=optional_manifest_path(data, "prefix"),
        module_root=optional_manifest_path(data, "module_root"),
        description=optional_string(data, "description"),
        homepage=optional_string(data, "homepage"),
        make_default=optional_bool(data, "default", True),
    )


def parse_environment_tool(data: object, base_dir: Path, index: int) -> EnvironmentToolSpec:
    """Parse one tool entry from a collective environment manifest.

    Args:
        data: Raw TOML table for the tool.
        base_dir: Manifest directory used to resolve relative files.
        index: One-based tool index for error messages.

    Returns:
        Parsed tool specification.

    Raises:
        TypeError: If the entry is not a table or has invalid values.
    """
    if not isinstance(data, dict):
        msg = f"tools[{index}] must be a TOML table"
        raise TypeError(msg)

    tool_type = require_string(data, "type")
    name = require_string(data, "name")
    tool = EnvironmentToolSpec(
        tool_type=tool_type,
        name=name,
        version=optional_string(data, "version"),
        package=optional_string(data, "package"),
        uv_config_file=optional_manifest_path(data, "uv_config_file", base_dir),
        uv_executable=optional_manifest_path(data, "uv_executable", base_dir),
        binary=optional_manifest_path(data, "binary", base_dir),
        script=optional_manifest_path(data, "script", base_dir),
        python=optional_string(data, "python"),
        indexes=optional_string_tuple(data, "indexes"),
        default_index=optional_string(data, "default_index"),
        find_links=optional_string_tuple(data, "find_links"),
        no_index=optional_bool(data, "no_index", False),
        index_strategy=optional_string(data, "index_strategy"),
        keyring_provider=optional_string(data, "keyring_provider"),
        constraints=tuple(str(path) for path in optional_manifest_paths(data, "constraints", base_dir)),
        no_cache=optional_bool(data, "no_cache", False),
        refresh=optional_bool(data, "refresh", False),
        refresh_packages=optional_string_tuple(data, "refresh_packages"),
        force=optional_bool(data, "force", False),
        reinstall=optional_bool(data, "reinstall", False),
        description=optional_string(data, "description"),
        homepage=optional_string(data, "homepage"),
    )
    validate_environment_tool(tool, index)
    return tool


def validate_environment_tool(tool: EnvironmentToolSpec, index: int) -> None:
    """Validate type-specific fields for one environment tool.

    Args:
        tool: Tool specification to validate.
        index: One-based tool index for error messages.

    Raises:
        TypeError: If required type-specific fields are missing.
    """
    if tool.tool_type == "python":
        if not tool.package:
            msg = f"tools[{index}].package is required for python tools"
            raise TypeError(msg)
        if tool.index_strategy and tool.index_strategy not in VALID_INDEX_STRATEGIES:
            msg = f"tools[{index}].index_strategy must be one of: {', '.join(VALID_INDEX_STRATEGIES)}"
            raise TypeError(msg)
        if tool.keyring_provider and tool.keyring_provider not in VALID_KEYRING_PROVIDERS:
            msg = f"tools[{index}].keyring_provider must be one of: {', '.join(VALID_KEYRING_PROVIDERS)}"
            raise TypeError(msg)
        return
    if tool.tool_type == "rust":
        if not tool.binary:
            msg = f"tools[{index}].binary is required for rust tools"
            raise TypeError(msg)
        return
    if tool.tool_type == "script":
        if not tool.script:
            msg = f"tools[{index}].script is required for script tools"
            raise TypeError(msg)
        return
    msg = f"tools[{index}].type must be one of: python, rust, script"
    raise TypeError(msg)


def environment_actions(
    spec: EnvironmentSpec,
    paths: DeploymentPaths,
    uv_executable: Path | None = None,
) -> tuple[str, ...]:
    """Build human-readable actions for a collective environment deployment.

    Args:
        spec: Collective environment specification.
        paths: Deployment paths for the environment module.
        uv_executable: Optional default uv executable path.

    Returns:
        Planned deployment actions.
    """
    actions = [
        f"create install root: {paths.install_root}",
        f"create bin dir: {paths.bin_dir}",
    ]
    tool_dir = paths.install_root / "uv-tools"
    for tool in spec.tools:
        if tool.tool_type == "python" and tool.package:
            command = uv_install_command(
                tool.package,
                tool.python,
                tool.indexes,
                tool.default_index,
                tool.find_links,
                tool.no_index,
                tool.index_strategy,
                tool.keyring_provider,
                tool.constraints,
                tool.no_cache,
                tool.refresh,
                tool.refresh_packages,
                tool.force,
                tool.reinstall,
                tool.uv_config_file,
                tool.uv_executable or uv_executable,
            )
            actions.append(
                f"install python {tool.name}: "
                f"UV_TOOL_DIR={shlex.quote(str(tool_dir))} "
                f"UV_TOOL_BIN_DIR={shlex.quote(str(paths.bin_dir))} "
                f"{shlex.join(command)}"
            )
        elif tool.tool_type == "rust" and tool.binary:
            actions.append(f"copy rust {tool.name}: {tool.binary} -> {paths.bin_dir / tool.name}")
        elif tool.tool_type == "script" and tool.script:
            actions.append(f"copy script {tool.name}: {tool.script} -> {paths.bin_dir / tool.name}")

    actions.append(f"write modulefile: {paths.modulefile}")
    if spec.make_default and paths.default_version_file:
        actions.append(f"write default version: {paths.default_version_file}")
    return tuple(actions)


def deploy_environment(
    *,
    spec: EnvironmentSpec,
    module_root: Path,
    prefix: Path,
    uv_executable: Path | None = None,
    dry_run: bool = False,
) -> EnvironmentDeploymentResult:
    """Deploy or preview a collective environment.

    Args:
        spec: Collective environment specification.
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        uv_executable: Optional default uv executable path.
        dry_run: Whether to report actions without mutating the filesystem.

    Returns:
        Deployment result with paths and action summaries.

    Raises:
        MissingExecutableError: If uv is needed but unavailable.
        subprocess.CalledProcessError: If `uv tool install` fails.
    """
    paths = deployment_paths(module_root, prefix, spec.name, spec.version)
    actions = environment_actions(spec, paths, uv_executable)

    if dry_run:
        return EnvironmentDeploymentResult(paths=paths, actions=actions)

    install_root_existed = paths.install_root.exists()
    modulefile_existed = paths.modulefile.exists()
    try:
        paths.bin_dir.mkdir(parents=True, exist_ok=True)
        tool_dir = paths.install_root / "uv-tools"
        for tool in spec.tools:
            if tool.tool_type == "python" and tool.package:
                resolved_uv_executable = tool.uv_executable or uv_executable
                require_executable(str(resolved_uv_executable or "uv"))
                subprocess.run(
                    uv_install_command(
                        tool.package,
                        tool.python,
                        tool.indexes,
                        tool.default_index,
                        tool.find_links,
                        tool.no_index,
                        tool.index_strategy,
                        tool.keyring_provider,
                        tool.constraints,
                        tool.no_cache,
                        tool.refresh,
                        tool.refresh_packages,
                        tool.force,
                        tool.reinstall,
                        tool.uv_config_file,
                        resolved_uv_executable,
                    ),
                    check=True,
                    env=uv_install_environment(tool_dir, paths.bin_dir),
                )
            elif tool.tool_type == "rust" and tool.binary:
                copy_executable(tool.binary, paths.bin_dir / tool.name)
            elif tool.tool_type == "script" and tool.script:
                copy_executable(tool.script, paths.bin_dir / tool.name)

        tool_names = ", ".join(tool.name for tool in spec.tools)
        install_hint = f"collective environment containing: {tool_names}"
        modulefile = render_modulefile(
            ModuleSpec(
                name=spec.name,
                version=spec.version,
                root=paths.install_root,
                bin_dir=paths.bin_dir,
                description=spec.description,
                homepage=spec.homepage,
                install_hint=install_hint,
            )
        )
        write_text(paths.modulefile, modulefile)
        write_default_version(paths, spec.version, spec.make_default)
    except Exception:
        rollback_deployment(paths, install_root_existed, modulefile_existed)
        raise
    return EnvironmentDeploymentResult(paths=paths, actions=actions)


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
    default_index: str | None = None,
    find_links: tuple[str, ...] = (),
    no_index: bool = False,
    index_strategy: str | None = None,
    keyring_provider: str | None = None,
    constraints: tuple[str, ...] = (),
    no_cache: bool = False,
    refresh: bool = False,
    refresh_packages: tuple[str, ...] = (),
    force: bool = False,
    reinstall: bool = False,
    uv_config_file: Path | None = None,
    uv_executable: Path | None = None,
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
        default_index: Default package index URL passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        no_index: Whether uv should ignore registry indexes.
        index_strategy: Package index strategy passed to uv.
        keyring_provider: Keyring provider passed to uv.
        constraints: Constraint requirement files passed to uv.
        no_cache: Whether uv should avoid reading from or writing to cache.
        refresh: Whether uv should refresh cached data.
        refresh_packages: Packages whose cached data uv should refresh.
        force: Whether uv should replace existing executable entries.
        reinstall: Whether uv should reinstall all packages.
        uv_config_file: Optional uv configuration file passed to `uv tool`.
        uv_executable: Optional uv executable path.
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
    install_root_existed = paths.install_root.exists()
    modulefile_existed = paths.modulefile.exists()
    try:
        paths.bin_dir.mkdir(parents=True, exist_ok=True)
        tool_dir = paths.install_root / "uv-tools"
        command = uv_install_command(
            package,
            python,
            indexes,
            default_index,
            find_links,
            no_index,
            index_strategy,
            keyring_provider,
            constraints,
            no_cache,
            refresh,
            refresh_packages,
            force,
            reinstall,
            uv_config_file,
            uv_executable,
        )

        if execute_install:
            require_executable(str(uv_executable or "uv"))
            subprocess.run(command, check=True, env=uv_install_environment(tool_dir, paths.bin_dir))

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
    except Exception:
        rollback_deployment(paths, install_root_existed, modulefile_existed)
        raise
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
    dry_run: bool = False,
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
        dry_run: Whether to report paths without mutating the filesystem.

    Returns:
        Paths created or targeted by the deployment.
    """
    return deploy_copied_tool(
        name=name,
        version=version,
        module_root=module_root,
        prefix=prefix,
        source=binary,
        description=description,
        homepage=homepage,
        make_default=make_default,
        dry_run=dry_run,
        install_label="binary",
    )


def deploy_copied_tool(
    *,
    name: str,
    version: str,
    module_root: Path,
    prefix: Path,
    source: Path | None,
    description: str | None,
    homepage: str | None,
    make_default: bool,
    dry_run: bool,
    install_label: str,
) -> DeploymentPaths:
    """Deploy metadata for a file copied into a versioned `bin` directory.

    Args:
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        module_root: Root of the environment module tree.
        prefix: Root installation prefix for deployed tools.
        source: Optional file to copy into the deployed `bin` directory.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        make_default: Whether to make this version the module default.
        dry_run: Whether to report paths without mutating the filesystem.
        install_label: Human-readable copied file type for module help.

    Returns:
        Paths created or targeted by the deployment.
    """
    paths = deployment_paths(module_root, prefix, name, version)
    if dry_run:
        return paths

    install_root_existed = paths.install_root.exists()
    modulefile_existed = paths.modulefile.exists()
    try:
        if source:
            copy_executable(source, paths.bin_dir / name)
        else:
            paths.bin_dir.mkdir(parents=True, exist_ok=True)

        modulefile = render_modulefile(
            ModuleSpec(
                name=name,
                version=version,
                root=paths.install_root,
                bin_dir=paths.bin_dir,
                description=description,
                homepage=homepage,
                install_hint=f"copy {install_label} to {paths.bin_dir / name}",
            )
        )
        write_text(paths.modulefile, modulefile)
        write_default_version(paths, version, make_default)
    except Exception:
        rollback_deployment(paths, install_root_existed, modulefile_existed)
        raise
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
    dry_run: bool = False,
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
        dry_run: Whether to report paths without mutating the filesystem.

    Returns:
        Paths created or targeted by the deployment.
    """
    return deploy_copied_tool(
        name=name,
        version=version,
        module_root=module_root,
        prefix=prefix,
        source=script,
        description=description,
        homepage=homepage,
        make_default=make_default,
        dry_run=dry_run,
        install_label="script",
    )
