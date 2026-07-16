"""Rendering helpers for GNU/Tcl environment modulefiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ENVIRONMENT_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def tcl_quote(value: str) -> str:
    """Quote a string for the small Tcl subset used in modulefiles.

    Args:
        value: Raw string to quote for Tcl modulefile output.

    Returns:
        A double-quoted Tcl string with backslashes, double quotes, and dollar
        signs escaped.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
    return f'"{escaped}"'


def parse_environment_variables(values: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    """Parse command-line environment variable assignments.

    Args:
        values: Assignments in `NAME=VALUE` form.

    Returns:
        Validated environment variable name/value pairs.

    Raises:
        ValueError: If an assignment has no equals sign, a name is invalid, or a
            name occurs more than once.
    """
    variables: list[tuple[str, str]] = []
    names: set[str] = set()
    for value in values:
        name, separator, variable_value = value.partition("=")
        if not separator or not ENVIRONMENT_VARIABLE_NAME.fullmatch(name):
            msg = f"Invalid environment variable {value!r}; use NAME=VALUE."
            raise ValueError(msg)
        if name in names:
            msg = f"Environment variable {name!r} was specified more than once."
            raise ValueError(msg)
        names.add(name)
        variables.append((name, variable_value))
    return tuple(variables)


@dataclass(frozen=True)
class ModuleSpec:
    """Data required to render one versioned environment modulefile.

    Attributes:
        name: Tool name used in the module path and root environment variable.
        version: Tool version used in the module path.
        root: Versioned installation root for the tool.
        bin_dir: Directory prepended to `PATH` by the generated modulefile.
        description: Optional text for `module-whatis` and `module help`.
        family: Optional Environment Modules family declaration.
        homepage: Optional upstream homepage shown in `module help`.
        install_hint: Optional installation command or note shown in
            `module help`.
        environment: Environment variables exported when the module loads.
    """

    name: str
    version: str
    root: Path
    bin_dir: Path
    description: str | None = None
    family: str | None = None
    homepage: str | None = None
    install_hint: str | None = None
    environment: tuple[tuple[str, str], ...] = ()

    @property
    def module_path(self) -> str:
        """Return the canonical module name/version path.

        Returns:
            Module path in `<name>/<version>` form.
        """
        return f"{self.name}/{self.version}"


def render_modulefile(spec: ModuleSpec) -> str:
    """Render a Tcl modulefile for the given module specification.

    Args:
        spec: Module metadata and filesystem paths to render.

    Returns:
        Tcl modulefile content.
    """
    description = spec.description or f"{spec.name} {spec.version}"
    lines = [
        "#%Module1.0",
        f"## {spec.module_path}",
        "",
        "proc ModulesHelp { } {",
        f"    puts stderr {tcl_quote(description)}",
    ]

    if spec.homepage:
        lines.append(f"    puts stderr {tcl_quote('Homepage: ' + spec.homepage)}")
    if spec.install_hint:
        lines.append(f"    puts stderr {tcl_quote('Install: ' + spec.install_hint)}")

    lines.extend(
        [
            "}",
            "",
            f"module-whatis {tcl_quote(description)}",
        ]
    )

    if spec.family:
        lines.append(f"family {tcl_quote(spec.family)}")

    environment = parse_environment_variables(tuple(f"{name}={value}" for name, value in spec.environment))

    lines.extend(
        [
            "",
            f"set root {tcl_quote(str(spec.root))}",
            f"set bindir {tcl_quote(str(spec.bin_dir))}",
            "",
            "prepend-path PATH $bindir",
            f"setenv {spec.name.upper().replace('-', '_')}_ROOT $root",
        ]
    )
    lines.extend(f"setenv {name} {tcl_quote(value)}" for name, value in environment)
    lines.append("")
    return "\n".join(lines)


def render_default_version(version: str) -> str:
    """Render the Environment Modules default-version selector file.

    Args:
        version: Module version to make the default.

    Returns:
        Tcl content for a `.version` selector file.
    """
    lines = [
        "#%Module1.0",
        f"set ModulesVersion {tcl_quote(version)}",
        "",
    ]
    return "\n".join(lines)


def is_default_version(content: str, version: str) -> bool:
    """Return whether default-version file content selects a version.

    Args:
        content: Existing `.version` file content.
        version: Version expected to be selected by the file.

    Returns:
        `True` when the content exactly selects `version`.
    """
    return content.strip() == render_default_version(version).strip()
