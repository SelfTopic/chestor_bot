import pytest

from src.bot.utils.calculator import CalculatorError, evaluate


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("2+2", 4),
        (" 2 + 2 * 10 ", 22),
        ("(2+2)*10", 40),
        ("2**10", 1024),
        ("-5+3", -2),
        ("+5", 5),
        ("10/4", 2.5),
        ("10//4", 2),
        ("10%3", 1),
    ],
)
def test_evaluate_valid_expressions(expression, expected):
    assert evaluate(expression) == expected


def test_evaluate_division_by_zero_raises_calculator_error():
    with pytest.raises(CalculatorError):
        evaluate("1/0")


def test_evaluate_invalid_syntax_raises_calculator_error():
    with pytest.raises(CalculatorError):
        evaluate("2 + + +")


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo hi')",
        "open('/etc/passwd')",
        "[1, 2, 3]",
        "True",
        "1 if 1 else 2",
        "a + 1",
    ],
)
def test_evaluate_rejects_anything_beyond_arithmetic(expression):
    """Не eval() - имена/вызовы/литералы коллекций/булевы значения и т.п.
    должны отклоняться на этапе разбора AST, а не пытаться выполниться."""

    with pytest.raises(CalculatorError):
        evaluate(expression)


def test_evaluate_rejects_huge_power_exponent():
    """2 ** 10_000_000 без ограничения кладёт CPU/память одним сообщением -
    регрессия на случай, если лимит будет случайно убран."""

    with pytest.raises(CalculatorError):
        evaluate("2 ** 10000000")


# --- require_operator (пассивный триггер в чате, fun_router.py) --------------


@pytest.mark.parametrize("expression", ["5", "-5", "+5", " 42 "])
def test_require_operator_rejects_bare_numbers(expression):
    with pytest.raises(CalculatorError):
        evaluate(expression, require_operator=True)


@pytest.mark.parametrize(
    "expression,expected",
    [("2+2", 4), ("-(2+3)", -5), ("(2+2)*10", 40), ("2**10", 1024)],
)
def test_require_operator_allows_real_expressions(expression, expected):
    assert evaluate(expression, require_operator=True) == expected


def test_require_operator_false_by_default_still_allows_bare_numbers():
    """require_operator по умолчанию False - явная команда "посчитай"
    (если она вообще где-то останется) не должна внезапно сломаться на
    голых числах."""

    assert evaluate("5") == 5
