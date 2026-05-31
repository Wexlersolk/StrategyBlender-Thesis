from __future__ import annotations

import ast
from .models import ON_BAR_ALLOWED_NAMES

class ExpressionValidator(ast.NodeVisitor):
    def __init__(self, allowed_names: set[str]):
        self.allowed_names = allowed_names

    def visit_Name(self, node: ast.Name):
        if node.id not in self.allowed_names:
            raise ValueError(f"Unsupported name in expression: {node.id}")

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__"):
            raise ValueError("Dunder attribute access is not allowed in strategy expressions")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id not in self.allowed_names:
            raise ValueError(f"Unsupported function in expression: {node.func.id}")
        self.generic_visit(node)

    def generic_visit(self, node: ast.AST):
        allowed_nodes = (
            ast.Expression,
            ast.BoolOp,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.Call,
            ast.Name,
            ast.Load,
            ast.Attribute,
            ast.Subscript,
            ast.Slice,
            ast.Constant,
            ast.Tuple,
            ast.List,
            ast.Dict,
            ast.keyword,
            ast.And,
            ast.Or,
            ast.Not,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.FloorDiv,
            ast.Mod,
            ast.Pow,
            ast.BitAnd,
            ast.BitOr,
            ast.BitXor,
            ast.Invert,
            ast.USub,
            ast.UAdd,
        )
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"Unsupported expression node: {type(node).__name__}")
        super().generic_visit(node)


def validate_expression(expr: str, allowed_names: set[str] = ON_BAR_ALLOWED_NAMES):
    parsed = ast.parse(expr, mode="eval")
    ExpressionValidator(allowed_names).visit(parsed)
