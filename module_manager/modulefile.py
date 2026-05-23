"""Rendering helpers for GNU/Tcl environment modulefiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    """

    name: str
    version: str
    root: Path
    bin_dir: Path
    description: str | None = None
    family: str | None = None
    homepage: str | None = None
    install_hint: str | None = None

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

    lines.extend(
        [
            "",
            f"set root {tcl_quote(str(spec.root))}",
            f"set bindir {tcl_quote(str(spec.bin_dir))}",
            "",
            "prepend-path PATH $bindir",
            f"setenv {spec.name.upper().replace('-', '_')}_ROOT $root",
            "",
        ]
    )
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
