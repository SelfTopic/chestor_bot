"""Безопасный калькулятор простых арифметических выражений - НЕ через
`eval()` (позволил бы выполнить произвольный Python-код из сообщения
пользователя). Разбирает выражение в AST и явно проверяет каждый узел по
белому списку разрешённых операций - имена, вызовы функций, атрибуты и
т.п. отклоняются на этапе разбора, а не пытаются быть "почищены" регуляркой."""

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

_MAX_POWER_EXPONENT = 1000
"""Ограничение на показатель степени - `2 ** 10_000_000` без него легко
кладёт процесс на секунды CPU и гигабайты памяти одним сообщением."""


class CalculatorError(ValueError):
    """Невалидное выражение или запрещённая операция - текст сообщения
    уже человекочитаемый, роутер отдаёт его как есть."""


def evaluate(expression: str) -> Number:
    """Считает арифметическое выражение (+, -, *, /, //, %, **, унарные
    +/-, скобки) и возвращает число. Бросает `CalculatorError` на любое
    невалидное или запрещённое выражение (не просто "ошибка", а с
    объяснением, что именно не так)."""

    try:
        # ast.parse(mode="eval") трактует ведущий пробел/отступ как
        # SyntaxError ("unexpected indent"), хотя это валидное выражение -
        # .strip() убирает эту неожиданность для вызывающего кода.
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("Не удалось разобрать выражение.") from exc

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

        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_POWER_EXPONENT:
            raise CalculatorError(
                f"Показатель степени слишком большой (максимум {_MAX_POWER_EXPONENT})."
            )

        return op_func(left, right)

    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise CalculatorError("Эта операция не поддерживается.")
        return op_func(_eval_node(node.operand))

    raise CalculatorError("Разрешены только числа, +, -, *, /, //, %, ** и скобки.")


__all__ = ["evaluate", "CalculatorError"]
