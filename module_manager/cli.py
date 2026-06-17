"""Command-line interface for deploying CLI tools as environment modules."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import rich_click as click
import tomllib
from click import Command

from . import __version__
from .config import AppConfig, load_config
from .deploy import (
    ConstraintGenerationError,
    EnvironmentDeploymentResult,
    UninstallResult,
    deploy_environment,
    deploy_python_tool,
    deploy_rust_tool,
    deploy_script_tool,
    generate_constraints,
    load_environment_spec,
    uninstall_tool,
)

click.rich_click.TEXT_MARKUP = "rich"
click.rich_click.STYLE_COMMAND = "bold cyan"
click.rich_click.STYLE_OPTION = "bold green"
click.rich_click.STYLE_ARGUMENT = "bold yellow"
click.rich_click.STYLE_SWITCH = "bold magenta"
click.rich_click.STYLE_METAVAR = "yellow"
click.rich_click.HEADER_TEXT = "module-manager"

PATH = click.Path(path_type=Path)
ClickCommand = TypeVar("ClickCommand", bound=Command)

TOP_LEVEL_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager deploy-python ruff 0.8.0 --package ruff==0.8.0 "
    "--prefix /prod/tools --module-root /prod/modulefiles[/cyan]\n\n"
    "[cyan]module-manager deploy-rust ripgrep 14.1.1 --binary ./target/release/rg "
    "--prefix /prod/tools --module-root /prod/modulefiles[/cyan]\n\n"
    "[cyan]module-manager deploy-script my-tool 1.0.0 --script ./scripts/my-tool "
    "--prefix /prod/tools --module-root /prod/modulefiles[/cyan]\n\n"
    "[cyan]module-manager auto-constraints ruff==0.8.0 --output constraints.txt[/cyan]\n\n"
    "[cyan]module-manager deploy-env --file dev-tools.toml[/cyan]\n\n"
    "[cyan]module-manager uninstall ruff 0.8.0 --prefix /prod/tools --module-root /prod/modulefiles[/cyan]"
)

DEPLOY_PYTHON_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager deploy-python ruff 0.8.0 --package ruff==0.8.0 "
    "--prefix /prod/tools --module-root /prod/modulefiles --execute-install[/cyan]\n\n"
    "[cyan]module-manager deploy-python internal-tool 1.2.3 --package internal-tool==1.2.3 "
    "--uv-config-file /prod/config/uv.toml --prefix /prod/tools --module-root /prod/modulefiles[/cyan]"
)

DEPLOY_RUST_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager deploy-rust ripgrep 14.1.1 --binary ./target/release/rg "
    "--prefix /prod/tools --module-root /prod/modulefiles[/cyan]\n\n"
    "[cyan]module-manager deploy-rust ripgrep 14.1.1 --binary ./target/release/rg "
    "--prefix /prod/tools --module-root /prod/modulefiles --dry-run[/cyan]"
)

DEPLOY_SCRIPT_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager deploy-script my-tool 1.0.0 --script ./scripts/my-tool "
    "--prefix /prod/tools --module-root /prod/modulefiles[/cyan]\n\n"
    "[cyan]module-manager deploy-script my-tool 1.0.0 --script ./scripts/my-tool "
    "--prefix /prod/tools --module-root /prod/modulefiles --dry-run[/cyan]"
)

DEPLOY_ENV_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager deploy-env --file dev-tools.toml[/cyan]\n\n"
    "[cyan]module-manager deploy-env --file dev-tools.toml --prefix /scratch/tools "
    "--module-root /scratch/modulefiles --dry-run[/cyan]"
)

AUTO_CONSTRAINTS_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager auto-constraints gitconductor==0.7.0[/cyan]\n\n"
    "[cyan]module-manager auto-constraints internal-tool==1.2.3 --index https://packages.example/simple "
    "--output /prod/constraints/internal-tool.txt[/cyan]"
)

UNINSTALL_EXAMPLES = (
    "Examples:\n\n"
    "[cyan]module-manager uninstall ruff 0.8.0 --prefix /prod/tools "
    "--module-root /prod/modulefiles[/cyan]\n\n"
    "[cyan]module-manager uninstall ruff 0.8.0 --prefix /prod/tools "
    "--module-root /prod/modulefiles --dry-run[/cyan]"
)


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


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "[bold]Deploy CLI tools behind GNU environment modulefiles.[/bold]\n\n"
        "Build versioned modulefiles for Python tools, Rust binaries, shell scripts, "
        "and collective environments."
    ),
    epilog=TOP_LEVEL_EXAMPLES,
)
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


@main.command(
    "deploy-python",
    help="Write a modulefile for a uv tool install Python CLI.",
    epilog=DEPLOY_PYTHON_EXAMPLES,
)
@common_options
@click.option("--package", "package", required=True, help="Package spec passed to uv tool install.")
@click.option("--python", "python", help="Python interpreter/version passed to uv.")
@click.option(
    "--index",
    "indexes",
    multiple=True,
    help="Additional package index URL passed to uv. May be used more than once.",
)
@click.option("--default-index", help="Default package index URL passed to uv.")
@click.option(
    "--find-links",
    "find_links",
    multiple=True,
    help="Directory or HTML page of packages passed to uv. May be used more than once.",
)
@click.option("--no-index", is_flag=True, help="Ignore registry indexes and use direct URLs or find-links.")
@click.option(
    "--index-strategy",
    type=click.Choice(["first-index", "unsafe-first-match", "unsafe-best-match"]),
    help="Package index strategy passed to uv.",
)
@click.option(
    "--keyring-provider",
    type=click.Choice(["disabled", "subprocess"]),
    help="Keyring provider passed to uv.",
)
@click.option(
    "--constraints",
    "constraints",
    multiple=True,
    help="Requirements constraint file passed to uv. May be used more than once.",
)
@click.option("--no-cache", is_flag=True, help="Avoid reading from or writing to the uv cache.")
@click.option("--refresh", is_flag=True, help="Refresh all uv cached data.")
@click.option(
    "--refresh-package",
    "refresh_packages",
    multiple=True,
    help="Refresh cached data for a package. May be used more than once.",
)
@click.option("--force", is_flag=True, help="Replace existing executable entries.")
@click.option("--reinstall", is_flag=True, help="Reinstall all packages in the tool environment.")
@click.option(
    "--uv-config-file",
    type=PATH,
    help="uv.toml file passed to uv tool install with --config-file.",
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
    default_index: str | None,
    find_links: tuple[str, ...],
    no_index: bool,
    index_strategy: str | None,
    keyring_provider: str | None,
    constraints: tuple[str, ...],
    no_cache: bool,
    refresh: bool,
    refresh_packages: tuple[str, ...],
    force: bool,
    reinstall: bool,
    uv_config_file: Path | None,
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
        default_index: Default package index URL passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        no_index: Whether uv should ignore registry indexes.
        index_strategy: Package index strategy passed to uv.
        keyring_provider: Keyring provider passed to uv.
        constraints: Requirements constraint files passed to uv.
        no_cache: Whether uv should avoid reading from or writing to cache.
        refresh: Whether uv should refresh cached data.
        refresh_packages: Packages whose cached data uv should refresh.
        force: Whether uv should replace existing executable entries.
        reinstall: Whether uv should reinstall all packages.
        uv_config_file: Optional uv configuration file passed to `uv tool`.
        execute_install: Whether to run `uv tool install` immediately.

    Raises:
        click.UsageError: If required paths are missing.
        MissingExecutableError: If `execute_install` is true and uv is not on
            `PATH`.
        subprocess.CalledProcessError: If `uv tool install` fails.
    """
    resolved_module_root, resolved_prefix = require_locations(
        module_root or config.module_root,
        prefix or config.prefix,
    )
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
        default_index=default_index,
        find_links=find_links or config.find_links,
        no_index=no_index,
        index_strategy=index_strategy,
        keyring_provider=keyring_provider,
        constraints=constraints,
        no_cache=no_cache,
        refresh=refresh,
        refresh_packages=refresh_packages,
        force=force,
        reinstall=reinstall,
        uv_config_file=(uv_config_file.expanduser() if uv_config_file else config.uv_config_file),
        execute_install=execute_install,
        make_default=make_default,
    )
    print_result(
        paths.modulefile, paths.install_root, paths.bin_dir, paths.default_version_file if make_default else None
    )


@main.command(
    "auto-constraints",
    help="Generate constraints for a Python package with uv.",
    epilog=AUTO_CONSTRAINTS_EXAMPLES,
)
@click.argument("package")
@click.option(
    "--output",
    "output_file",
    type=PATH,
    default=Path("constraints.txt"),
    show_default=True,
    help="Constraints file to write.",
)
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
    "--uv-config-file",
    type=PATH,
    help="uv.toml file passed to uv with --config-file.",
)
@click.pass_obj
def auto_constraints(
    config: AppConfig,
    package: str,
    output_file: Path,
    python: str | None,
    indexes: tuple[str, ...],
    find_links: tuple[str, ...],
    uv_config_file: Path | None,
) -> None:
    """Generate a constraints file for a Python package.

    Args:
        config: Resolved application configuration from the Click context.
        package: Package requirement to compile.
        output_file: Constraints file to write.
        python: Optional Python interpreter or version passed to uv.
        indexes: Additional package index URLs passed to uv.
        find_links: Wheelhouse directories or HTML package pages passed to uv.
        uv_config_file: Optional uv configuration file passed to uv.

    Raises:
        click.ClickException: If uv cannot generate constraints.
        MissingExecutableError: If uv is not on `PATH`.
    """
    try:
        result = generate_constraints(
            package=package,
            output_file=output_file.expanduser(),
            python=python,
            indexes=indexes or config.indexes,
            find_links=find_links or config.find_links,
            uv_config_file=(uv_config_file.expanduser() if uv_config_file else config.uv_config_file),
        )
    except ConstraintGenerationError as error:
        raise click.ClickException(str(error)) from error

    click.echo(f"constraints: {result.output_file}")
    if result.discovered_url_dependencies:
        click.echo(f"discovered URL dependencies: {len(result.discovered_url_dependencies)}")
        for requirement in result.discovered_url_dependencies:
            click.echo(f"  {requirement}")


@main.command(
    "deploy-rust",
    help="Copy a Rust CLI binary and write a modulefile for it.",
    epilog=DEPLOY_RUST_EXAMPLES,
)
@common_options
@click.option(
    "--binary",
    type=PATH,
    help="Compiled binary to copy into the versioned prefix.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print paths that would be written without creating files.",
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
    dry_run: bool,
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
        dry_run: Whether to report paths without mutating the filesystem.

    Raises:
        click.UsageError: If required paths are missing.
    """
    resolved_module_root, resolved_prefix = require_locations(
        module_root or config.module_root,
        prefix or config.prefix,
    )
    paths = deploy_rust_tool(
        name=name,
        version=version,
        module_root=resolved_module_root,
        prefix=resolved_prefix,
        binary=binary.expanduser() if binary else None,
        description=description,
        homepage=homepage,
        make_default=make_default,
        dry_run=dry_run,
    )
    print_result(
        paths.modulefile,
        paths.install_root,
        paths.bin_dir,
        paths.default_version_file if make_default else None,
        dry_run,
    )


@main.command(
    "deploy-script",
    help="Copy a shell script and write a modulefile for it.",
    epilog=DEPLOY_SCRIPT_EXAMPLES,
)
@common_options
@click.option(
    "--script",
    type=PATH,
    help="Shell script to copy into the versioned prefix.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print paths that would be written without creating files.",
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
    dry_run: bool,
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
        dry_run: Whether to report paths without mutating the filesystem.

    Raises:
        click.UsageError: If required paths are missing.
    """
    resolved_module_root, resolved_prefix = require_locations(
        module_root or config.module_root,
        prefix or config.prefix,
    )
    paths = deploy_script_tool(
        name=name,
        version=version,
        module_root=resolved_module_root,
        prefix=resolved_prefix,
        script=script.expanduser() if script else None,
        description=description,
        homepage=homepage,
        make_default=make_default,
        dry_run=dry_run,
    )
    print_result(
        paths.modulefile,
        paths.install_root,
        paths.bin_dir,
        paths.default_version_file if make_default else None,
        dry_run,
    )


@main.command(
    "deploy-env",
    help="Deploy a collective environment from a TOML manifest.",
    epilog=DEPLOY_ENV_EXAMPLES,
)
@click.option(
    "--file",
    "manifest",
    type=PATH,
    required=True,
    help="TOML collective environment manifest.",
)
@click.option(
    "--prefix",
    type=PATH,
    help="Root installation prefix, overriding manifest and config defaults.",
)
@click.option(
    "--module-root",
    type=PATH,
    help="Root of the module tree, overriding manifest and config defaults.",
)
@click.option(
    "--default/--no-default",
    "make_default",
    default=None,
    help="Override whether the manifest writes a module default selector.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print actions that would run without creating files.",
)
@click.pass_obj
def deploy_env(
    config: AppConfig,
    manifest: Path,
    module_root: Path | None,
    prefix: Path | None,
    make_default: bool | None,
    dry_run: bool,
) -> None:
    """Deploy a collective environment from a TOML manifest.

    Args:
        config: Resolved application configuration from the Click context.
        manifest: TOML collective environment manifest path.
        module_root: Optional module tree root overriding manifest and
            configuration.
        prefix: Optional install prefix overriding manifest and configuration.
        make_default: Optional override for manifest default behavior.
        dry_run: Whether to report actions without mutating the filesystem.

    Raises:
        click.ClickException: If the manifest cannot be parsed.
        click.UsageError: If required paths are missing.
    """
    try:
        spec = load_environment_spec(manifest)
    except (OSError, TypeError, tomllib.TOMLDecodeError) as error:
        raise click.ClickException(str(error)) from error

    resolved_module_root, resolved_prefix = require_locations(
        module_root or spec.module_root or config.module_root,
        prefix or spec.prefix or config.prefix,
    )
    if make_default is not None:
        spec = spec.__class__(
            name=spec.name,
            version=spec.version,
            tools=spec.tools,
            prefix=spec.prefix,
            module_root=spec.module_root,
            description=spec.description,
            homepage=spec.homepage,
            make_default=make_default,
        )

    result = deploy_environment(spec=spec, module_root=resolved_module_root, prefix=resolved_prefix, dry_run=dry_run)
    print_environment_result(result, dry_run)


@main.command(
    "uninstall",
    help="Remove a deployed tool version and its modulefile.",
    epilog=UNINSTALL_EXAMPLES,
)
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
    resolved_module_root, resolved_prefix = require_locations(
        module_root or config.module_root,
        prefix or config.prefix,
    )
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


def require_locations(module_root: Path | None, prefix: Path | None) -> tuple[Path, Path]:
    """Return distinct configured module and installation roots.

    Args:
        module_root: Candidate root of the module tree.
        prefix: Candidate installation prefix.

    Returns:
        Expanded module root and installation prefix.

    Raises:
        click.UsageError: If either path is missing or both resolve to the same
            directory.
    """
    resolved_module_root = require_path(module_root, "module root", "--module-root")
    resolved_prefix = require_path(prefix, "install prefix", "--prefix")
    if resolved_module_root.resolve() == resolved_prefix.resolve():
        msg = (
            "--module-root and --prefix must resolve to different directories; "
            "otherwise the versioned modulefile collides with the install root."
        )
        raise click.UsageError(msg)
    return resolved_module_root, resolved_prefix


def print_result(
    modulefile: Path,
    install_root: Path,
    bin_dir: Path,
    default_version_file: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Print the paths produced by a deployment command.

    Args:
        modulefile: Versioned modulefile path.
        install_root: Versioned installation root.
        bin_dir: Executable directory exposed by the modulefile.
        default_version_file: Optional default selector path.
        dry_run: Whether the command only previewed writes.
    """
    prefix = "would write " if dry_run else ""
    click.echo(f"{prefix}modulefile: {modulefile}")
    click.echo(f"{prefix}install root: {install_root}")
    click.echo(f"{prefix}bin dir: {bin_dir}")
    if default_version_file:
        click.echo(f"{prefix}default version: {default_version_file}")


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


def print_environment_result(result: EnvironmentDeploymentResult, dry_run: bool = False) -> None:
    """Print actions produced by a collective environment deployment.

    Args:
        result: Collective environment deployment result.
        dry_run: Whether the command only previewed actions.
    """
    prefix = "would " if dry_run else ""
    for action in result.actions:
        click.echo(f"{prefix}{action}")
