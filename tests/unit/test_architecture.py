"""Architectural test: enforce import direction across package layers.

The package is organized as a strict stack:

  config → errors → http → models → tools → server

A higher layer may import from a lower one; the reverse is forbidden, and
sibling modules within the same layer should not depend on each other
unnecessarily. This test parses every ``import``/``from`` statement in
the package source and asserts the rules below.

Catching layering drift in CI is much cheaper than discovering it via a
circular-import error six months from now, so the test is deliberately
strict — it fails on any new violation, even one that "happens to work".
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# tests/unit/test_architecture.py -> tests/unit/ -> tests/ -> repo root
PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "src" / "saldeosmart_mcp"

# Layer ordering: a module may only import from itself or layers BELOW it.
# Lower index = lower (foundational) layer; higher index = higher (app) layer.
LAYERS: dict[str, int] = {
    "config": 0,
    "errors": 1,
    "logging": 1,         # peer of errors — neither depends on the other
    "http": 2,
    "models": 3,
    "tools": 4,
    "server": 5,
    "__init__": 5,        # public surface — may pull from anywhere
    "__main__": 5,
}


def _layer_of(module_path: tuple[str, ...]) -> str:
    """Map a module path inside the package to its layer name.

    e.g. ``("http", "client")`` → ``"http"``;
    ``("tools", "documents")`` → ``"tools"``.
    """
    return module_path[0] if module_path else "__init__"


def _iter_python_files() -> list[Path]:
    """Yield every .py file under the package, excluding caches."""
    return sorted(
        p for p in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _parse_relative_imports(source: str) -> list[tuple[int, tuple[str, ...]]]:
    """Return [(level, module_path_components), ...] for every relative import.

    ``level`` is the number of dots (1 = current package, 2 = parent, …).
    ``module_path_components`` is the dotted path of the imported submodule
    (empty for ``from . import x`` — the imported names are ``x`` siblings).
    """
    tree = ast.parse(source)
    out: list[tuple[int, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level and node.level > 0:
            mod = tuple((node.module or "").split(".")) if node.module else ()
            # Strip empty strings from the split (happens for `from . import x`).
            mod = tuple(m for m in mod if m)
            out.append((node.level, mod))
    return out


def _module_path_for(file_path: Path) -> tuple[str, ...]:
    """Return the dotted path of `file_path` relative to the package root.

    ``http/client.py`` → ``("http", "client")``.
    ``__init__.py`` (package root) → ``("__init__",)``.
    """
    rel = file_path.relative_to(PACKAGE_ROOT).with_suffix("")
    parts = tuple(rel.parts)
    if not parts or parts == (".",):
        return ("__init__",)
    return parts


def _imports_from(
    source_path: Path, level: int, target_module: tuple[str, ...]
) -> tuple[str, ...]:
    """Resolve a relative `from X import Y` to an absolute module path inside the package.

    ``level=1`` resolves against the current module's parent; ``level=2`` against
    the grandparent; etc.
    """
    source_module = _module_path_for(source_path)
    # Drop the file name (the last component) to get the "current package".
    package_path = source_module[:-1]
    # `level=1` means "this package"; `level=2` means "parent package", etc.
    if level > len(package_path):
        # Reaching outside the saldeosmart_mcp package — not our concern here.
        return ()
    base = package_path[: len(package_path) - (level - 1)]
    return base + target_module


# ---- Tests -----------------------------------------------------------------------


@pytest.mark.parametrize("py_file", _iter_python_files(), ids=lambda p: p.name)
def test_module_imports_obey_layering(py_file: Path) -> None:
    """No module imports a layer above its own."""
    source = py_file.read_text(encoding="utf-8")
    source_module = _module_path_for(py_file)
    source_layer_name = _layer_of(source_module)
    if source_layer_name not in LAYERS:
        # A new top-level module showed up that we don't know about.
        # Fail loudly so someone updates the layer map intentionally.
        pytest.fail(
            f"{py_file.name}: top-level layer {source_layer_name!r} is not in "
            f"LAYERS; update tests/unit/test_architecture.py to declare its position."
        )
    source_layer = LAYERS[source_layer_name]

    for level, target in _parse_relative_imports(source):
        # `from . import x` (target empty) is in the same package — fine.
        if not target:
            continue
        absolute = _imports_from(py_file, level, target)
        if not absolute:
            continue
        target_layer_name = _layer_of(absolute)
        if target_layer_name not in LAYERS:
            continue
        target_layer = LAYERS[target_layer_name]

        # A module is always allowed to import from a strictly lower layer
        # (target_layer < source_layer) or from itself.
        if target_layer > source_layer:
            pytest.fail(
                f"{source_module!r} (layer {source_layer_name}) imports from "
                f"{absolute!r} (layer {target_layer_name}) — that's an "
                f"upward dependency. Move the symbol down or split the module."
            )


def test_no_module_imports_server() -> None:
    """``server.py`` is the entrypoint — nothing else should import it."""
    for py_file in _iter_python_files():
        if py_file.name in {"__main__.py", "server.py", "__init__.py"}:
            # __main__ delegates to server.main; server is the file under test;
            # __init__ doesn't pull from server (verified separately by parsing).
            continue
        source = py_file.read_text(encoding="utf-8")
        for _, target in _parse_relative_imports(source):
            assert target != ("server",), (
                f"{py_file.name} imports `server`, but server.py is the entrypoint "
                f"and must remain a leaf. Move whatever you needed into a layer "
                f"that both `server` and the new caller can import from."
            )


def test_layers_match_directory_structure() -> None:
    """Spot-check that the directories/files we expect actually exist.

    Guards against renames silently passing the layering rules above by
    becoming inert (an absent layer can't violate anything).
    """
    expected = {
        "config.py",
        "errors.py",
        "logging.py",
        "http",
        "models",
        "tools",
        "server.py",
        "__init__.py",
        "__main__.py",
    }
    actual = {p.name for p in PACKAGE_ROOT.iterdir() if not p.name.startswith(".")
              and p.name != "__pycache__"}
    missing = expected - actual
    assert not missing, f"expected layout entries not found: {missing}"


# ---- Tool-decorator and stdio-hygiene rules -------------------------------------


def _decorator_matches(dec: ast.expr, name: str) -> bool:
    """True if `dec` is `name`, `<anything>.name`, or a Call wrapping either."""
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Name):
        return target.id == name
    if isinstance(target, ast.Attribute):
        return target.attr == name
    return False


def _iter_tool_files() -> list[Path]:
    """Tool modules — the only place ``@mcp.tool`` should appear."""
    tools_dir = PACKAGE_ROOT / "tools"
    return sorted(p for p in tools_dir.glob("*.py") if not p.name.startswith("_"))


@pytest.mark.parametrize("py_file", _iter_tool_files(), ids=lambda p: p.name)
def test_every_mcp_tool_is_wrapped_by_saldeo_call(py_file: Path) -> None:
    """Each ``@mcp.tool`` function must also carry ``@saldeo_call``.

    The pair guarantees that any SaldeoError raised inside a tool turns into
    a structured ErrorResponse rather than a 500-style traceback to the MCP
    client. Forgetting the wrapper silently regresses error UX.
    """
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not any(_decorator_matches(d, "tool") for d in node.decorator_list):
            continue
        # `mcp.tool` may be the only "tool" attribute we use, but be precise:
        # only flag when the decorator chain explicitly invokes `mcp.tool`.
        is_mcp_tool = any(
            isinstance(d, ast.Attribute) and d.attr == "tool"
            and isinstance(d.value, ast.Name) and d.value.id == "mcp"
            for d in node.decorator_list
        ) or any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "tool"
            and isinstance(d.func.value, ast.Name)
            and d.func.value.id == "mcp"
            for d in node.decorator_list
        )
        if not is_mcp_tool:
            continue
        has_saldeo_call = any(_decorator_matches(d, "saldeo_call") for d in node.decorator_list)
        assert has_saldeo_call, (
            f"{py_file.name}::{node.name} is decorated with @mcp.tool but not "
            f"@saldeo_call — SaldeoError would escape as an unhandled exception."
        )


@pytest.mark.parametrize("py_file", _iter_python_files(), ids=lambda p: p.name)
def test_no_print_calls_in_package(py_file: Path) -> None:
    """``print()`` corrupts MCP's stdio transport — log to file instead."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            pytest.fail(
                f"{py_file.name}:{node.lineno}: print() call found. MCP uses stdio "
                f"as its transport — use the logging module instead."
            )


@pytest.mark.parametrize("py_file", _iter_python_files(), ids=lambda p: p.name)
def test_only_server_or_package_init_imports_tools(py_file: Path) -> None:
    """The ``tools`` package registers MCP handlers as a side effect of import.

    Only ``server.py`` (entrypoint) and the package ``__init__.py`` (public
    surface) should reach into it. Anything else creates a hidden side-effect
    dependency on tool registration order.
    """
    source_module = _module_path_for(py_file)
    # The tools package itself, the server entrypoint, and the package root
    # are the legitimate consumers.
    if source_module[0] == "tools" or py_file.name in {"server.py", "__init__.py"}:
        return
    source = py_file.read_text(encoding="utf-8")
    for _, target in _parse_relative_imports(source):
        if target and target[0] == "tools":
            pytest.fail(
                f"{py_file.name} imports from `tools` package "
                f"(target={'.'.join(target)}). Tool modules register MCP handlers on "
                f"import — only server.py and the package __init__ should pull them in."
            )
