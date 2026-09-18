"""LibCST's concrete role (design.md DD14, proposal D2): a mechanical
guard over the generator's OWN Python source, never over emitted Java
and never called at render time. Parses every module under
`apps/spring_generator/emit/` with `libcst.parse_module` and fails on
string `+` concatenation, `str.join`, `%`-formatting, or any f-string
(`JoinedString`). `.format()` is not one of the four checked patterns.
"""
from pathlib import Path

import libcst as cst

_EMIT_DIR = Path(__file__).resolve().parent.parent / "emit"


class _ConcatenationVisitor(cst.CSTVisitor):
    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_FormattedString(self, node: cst.FormattedString) -> None:
        self.violations.append("f-string")

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> None:
        if isinstance(node.operator, cst.Add) and (
            _is_string_literal(node.left) or _is_string_literal(node.right)
        ):
            self.violations.append("string '+' concatenation")
        if isinstance(node.operator, cst.Modulo) and _is_string_literal(node.left):
            self.violations.append("'%' string formatting")

    def visit_Call(self, node: cst.Call) -> None:
        if isinstance(node.func, cst.Attribute) and node.func.attr.value == "join":
            self.violations.append("str.join")


def _is_string_literal(node: cst.BaseExpression) -> bool:
    return isinstance(node, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString))


def _emit_modules() -> list[Path]:
    return sorted(_EMIT_DIR.rglob("*.py"))


def test_emit_modules_exist():
    assert _emit_modules(), f"no Python modules found under {_EMIT_DIR}"


def test_no_manual_string_concatenation_in_emit_modules():
    offenders: dict[str, list[str]] = {}

    for module_path in _emit_modules():
        tree = cst.parse_module(module_path.read_text())
        visitor = _ConcatenationVisitor()
        tree.visit(visitor)
        if visitor.violations:
            offenders[str(module_path.relative_to(_EMIT_DIR))] = visitor.violations

    assert not offenders, f"manual string concatenation found: {offenders}"
