import ast
import operator
from typing import Union

Number = Union[int, float]

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Без предела `2 ** 10_000_000` одним сообщением занимает процесс на секунды.
MAX_POWER_EXPONENT = 1000


class CalculatorError(ValueError):
    pass


def evaluate(expression: str, *, require_operator: bool = False) -> Number:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("Не удалось разобрать выражение.") from exc

    if require_operator and not _has_binary_operator(tree.body):
        raise CalculatorError("Нет ни одного оператора.")

    try:
        result = _eval_node(tree.body)
    except ZeroDivisionError as exc:
        raise CalculatorError("Деление на ноль.") from exc

    if isinstance(result, complex):
        raise CalculatorError("Результат не является действительным числом.")

    return result


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise CalculatorError("Разрешены только числа.")
        return node.value

    if isinstance(node, ast.BinOp):
        op_func = _BIN_OPS.get(type(node.op))
        if op_func is None:
            raise CalculatorError("Эта операция не поддерживается.")

        left = _eval_node(node.left)
        right = _eval_node(node.right)

        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER_EXPONENT:
            raise CalculatorError(
                f"Показатель степени слишком большой (максимум {MAX_POWER_EXPONENT})."
            )

        return op_func(left, right)

    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise CalculatorError("Эта операция не поддерживается.")
        return op_func(_eval_node(node.operand))

    raise CalculatorError("Разрешены только числа, +, -, *, /, //, %, ** и скобки.")


def _has_binary_operator(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp):
        return True
    if isinstance(node, ast.UnaryOp):
        return _has_binary_operator(node.operand)
    return False
