"""Command-line interface for deploying CLI tools as environment modules."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import rich_click as click
from click import Command

from . import __version__
from .config import AppConfig, load_config
from .deploy import UninstallResult, deploy_python_tool, deploy_rust_tool, deploy_script_tool, uninstall_tool

click.rich_click.TEXT_MARKUP = "rich"
click.rich_click.STYLE_COMMAND = "bold cyan"
click.rich_click.STYLE_OPTION = "bold green"
click.rich_click.STYLE_ARGUMENT = "bold yellow"
click.rich_click.STYLE_SWITCH = "bold magenta"
click.rich_click.STYLE_METAVAR = "yellow"
click.rich_click.HEADER_TEXT = "module-manager"
click.rich_click.FOOTER_TEXT = (
    "Examples: [cyan]module-manager deploy-python ruff 0.8.0 --package "
    "ruff==0.8.0 --prefix /prod/tools --module-root /prod/modulefiles[/cyan]"
)

PATH = click.Path(path_type=Path)
ClickCommand = TypeVar("ClickCommand", bound=Command)


def common_options(command: ClickCommand) -> ClickCommand:
    """Attach options shared by deployment commands.

    Args:
        command: Click command function being decorated.

    Returns:
        Decorated Click command function.
    """
    command = click.option(
        "--default/--no-default",
        "make_default",
        default=True,
        show_default=True,
        help="Write the module default selector for this version.",
    )(command)
    command = click.option(
        "--homepage",
        help="Optional upstream homepage shown in module help.",
    )(command)
    command = click.option(
        "--description",
        help="Text shown by module help and module-whatis.",
    )(command)
    command = click.option(
        "--prefix",
        type=PATH,
        help="Root installation prefix, for example /prod/tools.",
    )(command)
    command = click.option(
        "--module-root",
        type=PATH,
        help="Root of the module tree, for example /prod/modulefiles.",
    )(command)
    command = click.argument("version")(command)
    command = click.argument("name")(command)
    return command


def location_options(command: ClickCommand) -> ClickCommand:
    """Attach options for commands that need deployment roots.

    Args:
        command: Click command function being decorated.

    Returns:
        Decorated Click command function.
    """
    command = click.option(
        "--prefix",
        type=PATH,
        help="Root installation prefix, for example /prod/tools.",
    )(command)
    command = click.option(
        "--module-root",
        type=PATH,
        help="Root of the module tree, for example /prod/modulefiles.",
    )(command)
    command = click.argument("version")(command)
    command = click.argument("name")(command)
    return command


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
@click.option(
    "--config",
    type=PATH,
    envvar="MODULE_MANAGER_CONFIG",
    help="TOML config path. Defaults to ~/.config/module-manager/config.toml.",
)
@click.pass_context
def main(ctx: click.Context, config: Path | None) -> None:
    """[bold]Deploy CLI tools behind GNU environment modulefiles.[/bold].

    Build versioned modulefiles for Python tools installed with
    [cyan]uv tool install[/cyan], Rust binaries, and shell scripts copied into
    a production prefix.

    Args:
        ctx: Click context used to store resolved configuration.
        config: Optional TOML configuration path.
    """
    ctx.obj = load_config(config)


@main.command("deploy-python")
@common_options
@click.option("--package", "package", required=True, help="Package spec passed to uv tool install.")
@click.option("--python", "python", help="Python interpreter/version passed to uv.")
@click.option(
    "--index",
    "indexes",
    multiple=True,
    help="Additional package index URL passed to uv. May be used more than once.",
)
@click.option(
    "--find-links",
    "find_links",
    multiple=True,
    help="Directory or HTML page of packages passed to uv. May be used more than once.",
)
@click.option(
    "--execute-install",
    is_flag=True,
    help="Run uv tool install before writing the modulefile.",
)
@click.pass_obj
def deploy_python(
    config: AppConfig,
    name: str,
    version: str,
    module_root: Path | None,
    prefix: Path | None,
    description: str | None,
    homepage: str | None,
    make_default: bool,
    package: str,
    python: str | None,
    indexes: tuple[str, ...],
    find_links: tuple[str, ...],
    execute_install: bool,
) -> None:
    """Write a modulefile for a [cyan]uv tool install[/cyan] Python CLI.

    Args:
        config: Resolved application configuration from the Click context.
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        module_root: Optional module tree root overriding configuration.
        prefix: Optional install prefix overriding configuration.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        make_default: Whether to make this version the module default.
        package: Package spec passed to `uv tool install`.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        execute_install: Whether to run `uv tool install` immediately.

    Raises:
        click.UsageError: If required paths are missing.
        MissingExecutableError: If `execute_install` is true and uv is not on
            `PATH`.
        subprocess.CalledProcessError: If `uv tool install` fails.
    """
    resolved_module_root = require_path(module_root or config.module_root, "module root", "--module-root")
    resolved_prefix = require_path(prefix or config.prefix, "install prefix", "--prefix")
    paths = deploy_python_tool(
        name=name,
        version=version,
        package=package,
        module_root=resolved_module_root,
        prefix=resolved_prefix,
        description=description,
        homepage=homepage,
        python=python,
        indexes=indexes or config.indexes,
        find_links=find_links or config.find_links,
        execute_install=execute_install,
        make_default=make_default,
    )
    print_result(
        paths.modulefile, paths.install_root, paths.bin_dir, paths.default_version_file if make_default else None
    )


@main.command("deploy-rust")
@common_options
@click.option(
    "--binary",
    type=PATH,
    help="Compiled binary to copy into the versioned prefix.",
)
@click.pass_obj
def deploy_rust(
    config: AppConfig,
    name: str,
    version: str,
    module_root: Path | None,
    prefix: Path | None,
    description: str | None,
    homepage: str | None,
    make_default: bool,
    binary: Path | None,
) -> None:
    """Copy a Rust CLI binary and write a modulefile for it.

    Args:
        config: Resolved application configuration from the Click context.
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        module_root: Optional module tree root overriding configuration.
        prefix: Optional install prefix overriding configuration.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        make_default: Whether to make this version the module default.
        binary: Optional compiled binary to copy into the deployed `bin`
            directory.

    Raises:
        click.UsageError: If required paths are missing.
    """
    resolved_module_root = require_path(module_root or config.module_root, "module root", "--module-root")
    resolved_prefix = require_path(prefix or config.prefix, "install prefix", "--prefix")
    paths = deploy_rust_tool(
        name=name,
        version=version,
        module_root=resolved_module_root,
        prefix=resolved_prefix,
        binary=binary.expanduser() if binary else None,
        description=description,
        homepage=homepage,
        make_default=make_default,
    )
    print_result(
        paths.modulefile, paths.install_root, paths.bin_dir, paths.default_version_file if make_default else None
    )


@main.command("deploy-script")
@common_options
@click.option(
    "--script",
    type=PATH,
    help="Shell script to copy into the versioned prefix.",
)
@click.pass_obj
def deploy_script(
    config: AppConfig,
    name: str,
    version: str,
    module_root: Path | None,
    prefix: Path | None,
    description: str | None,
    homepage: str | None,
    make_default: bool,
    script: Path | None,
) -> None:
    """Copy a shell script and write a modulefile for it.

    Args:
        config: Resolved application configuration from the Click context.
        name: Tool name used in install and module paths.
        version: Tool version used in install and module paths.
        module_root: Optional module tree root overriding configuration.
        prefix: Optional install prefix overriding configuration.
        description: Optional module help and `module-whatis` text.
        homepage: Optional upstream homepage shown in module help.
        make_default: Whether to make this version the module default.
        script: Optional shell script to copy into the deployed `bin` directory.

    Raises:
        click.UsageError: If required paths are missing.
    """
    resolved_module_root = require_path(module_root or config.module_root, "module root", "--module-root")
    resolved_prefix = require_path(prefix or config.prefix, "install prefix", "--prefix")
    paths = deploy_script_tool(
        name=name,
        version=version,
        module_root=resolved_module_root,
        prefix=resolved_prefix,
        script=script.expanduser() if script else None,
        description=description,
        homepage=homepage,
        make_default=make_default,
    )
    print_result(
        paths.modulefile, paths.install_root, paths.bin_dir, paths.default_version_file if make_default else None
    )


@main.command("uninstall")
@location_options
@click.option(
    "--keep-default",
    is_flag=True,
    help="Leave the default selector in place, even if it points at this version.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print paths that would be removed without deleting them.",
)
@click.pass_obj
def uninstall(
    config: AppConfig,
    name: str,
    version: str,
    module_root: Path | None,
    prefix: Path | None,
    keep_default: bool,
    dry_run: bool,
) -> None:
    """Remove a deployed tool version and its modulefile.

    Args:
        config: Resolved application configuration from the Click context.
        name: Tool name used in install and module paths.
        version: Tool version to remove.
        module_root: Optional module tree root overriding configuration.
        prefix: Optional install prefix overriding configuration.
        keep_default: Whether to leave the default selector untouched.
        dry_run: Whether to report paths without deleting them.

    Raises:
        click.UsageError: If required paths are missing.
    """
    resolved_module_root = require_path(module_root or config.module_root, "module root", "--module-root")
    resolved_prefix = require_path(prefix or config.prefix, "install prefix", "--prefix")
    result = uninstall_tool(
        name=name,
        version=version,
        module_root=resolved_module_root,
        prefix=resolved_prefix,
        remove_default=not keep_default,
        dry_run=dry_run,
    )
    print_uninstall_result(result, dry_run)


def require_path(value: Path | None, label: str, option: str) -> Path:
    """Return a configured path or raise a Click usage error.

    Args:
        value: Candidate path from CLI options or configuration.
        label: Human-readable path label used in the error message.
        option: CLI option that can provide the missing path.

    Returns:
        Expanded path.

    Raises:
        click.UsageError: If `value` is `None`.
    """
    if value is None:
        msg = (
            f"Missing {label}. Provide {option}, set the matching MODULE_MANAGER_* "
            "environment variable, or configure it in TOML."
        )
        raise click.UsageError(msg)
    return value.expanduser()


def print_result(
    modulefile: Path,
    install_root: Path,
    bin_dir: Path,
    default_version_file: Path | None = None,
) -> None:
    """Print the paths produced by a deployment command.

    Args:
        modulefile: Versioned modulefile path.
        install_root: Versioned installation root.
        bin_dir: Executable directory exposed by the modulefile.
        default_version_file: Optional default selector path.
    """
    click.echo(f"modulefile: {modulefile}")
    click.echo(f"install root: {install_root}")
    click.echo(f"bin dir: {bin_dir}")
    if default_version_file:
        click.echo(f"default version: {default_version_file}")


def print_uninstall_result(result: UninstallResult, dry_run: bool = False) -> None:
    """Print the paths removed by an uninstall command.

    Args:
        result: Uninstall result to report.
        dry_run: Whether the command only previewed removals.
    """
    action = "would remove" if dry_run else "removed"
    if not result.removed:
        click.echo("nothing to remove")
        return
    for path in result.removed:
        click.echo(f"{action}: {path}")
