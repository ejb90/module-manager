"""Command-line interface for deploying CLI tools as environment modules."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import rich_click as click
from click import Command

from . import __version__
from .config import AppConfig, load_config
from .deploy import deploy_python_tool, deploy_rust_tool

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
    """Attach options shared by Python and Rust deployment commands."""
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
    [cyan]uv tool install[/cyan] and Rust binaries copied into a production
    prefix.
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
    package: str,
    python: str | None,
    indexes: tuple[str, ...],
    find_links: tuple[str, ...],
    execute_install: bool,
) -> None:
    """Write a modulefile for a [cyan]uv tool install[/cyan] Python CLI."""
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
    )
    print_result(paths.modulefile, paths.install_root, paths.bin_dir)


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
    binary: Path | None,
) -> None:
    """Copy a Rust CLI binary and write a modulefile for it."""
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
    )
    print_result(paths.modulefile, paths.install_root, paths.bin_dir)


def require_path(value: Path | None, label: str, option: str) -> Path:
    """Return a configured path or raise a Click usage error."""
    if value is None:
        msg = (
            f"Missing {label}. Provide {option}, set the matching MODULE_MANAGER_* "
            "environment variable, or configure it in TOML."
        )
        raise click.UsageError(msg)
    return value.expanduser()


def print_result(modulefile: Path, install_root: Path, bin_dir: Path) -> None:
    """Print the paths produced by a deployment command."""
    click.echo(f"modulefile: {modulefile}")
    click.echo(f"install root: {install_root}")
    click.echo(f"bin dir: {bin_dir}")
