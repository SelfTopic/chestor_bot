import ast
import math
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

# Ответ должен уместиться в сообщение (4096 символов). Размер проверяется до вычисления:
# предел на один показатель не спасает от ((9**1000)**1000)**1000 — это минуты в event loop.
MAX_RESULT_DIGITS = 4000
MAX_RESULT_BITS = int(MAX_RESULT_DIGITS * math.log2(10))


class CalculatorError(ValueError):
    pass


class NotArithmetic(CalculatorError):
    pass


class DivisionByZero(CalculatorError):
    pass


class ResultTooBig(CalculatorError):
    pass


def evaluate(expression: str, *, require_operator: bool = False) -> Number:
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    # RecursionError — очень глубокая вложенность, ValueError — нулевой байт в тексте.
    except (SyntaxError, RecursionError, ValueError) as exc:
        raise NotArithmetic("Не удалось разобрать выражение.") from exc

    if require_operator and not _has_binary_operator(tree.body):
        raise NotArithmetic("Нет ни одного оператора.")

    try:
        result = _eval_node(tree.body)
    except ZeroDivisionError as exc:
        raise DivisionByZero("Деление на ноль.") from exc
    except OverflowError as exc:
        raise ResultTooBig("Результат слишком большой.") from exc
    except RecursionError as exc:
        raise NotArithmetic("Слишком глубокое выражение.") from exc

    if isinstance(result, complex):
        raise NotArithmetic("Результат не является действительным числом.")

    return result


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise NotArithmetic("Разрешены только числа.")
        return node.value

    if isinstance(node, ast.BinOp):
        op_func = _BIN_OPS.get(type(node.op))
        if op_func is None:
            raise NotArithmetic("Эта операция не поддерживается.")

        left = _eval_node(node.left)
        right = _eval_node(node.right)

        if (
            isinstance(node.op, ast.Pow)
            and isinstance(left, int)
            and isinstance(right, int)
            and left.bit_length() * right > MAX_RESULT_BITS
        ):
            raise ResultTooBig("Результат слишком большой.")

        return _checked(op_func(left, right))

    if isinstance(node, ast.UnaryOp):
        op_func = _UNARY_OPS.get(type(node.op))
        if op_func is None:
            raise NotArithmetic("Эта операция не поддерживается.")
        return op_func(_eval_node(node.operand))

    raise NotArithmetic("Разрешены только числа, +, -, *, /, //, %, ** и скобки.")


def _checked(value: Number) -> Number:
    if isinstance(value, int) and value.bit_length() > MAX_RESULT_BITS:
        raise ResultTooBig("Результат слишком большой.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ResultTooBig("Результат слишком большой.")
    return value


def _has_binary_operator(node: ast.AST) -> bool:
    if isinstance(node, ast.BinOp):
        return True
    if isinstance(node, ast.UnaryOp):
        return _has_binary_operator(node.operand)
    return False
