import time

import pytest

from src.bot.routers.common.fun.calculator import (
    DivisionByZero,
    NotArithmetic,
    ResultTooBig,
    evaluate,
)


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


@pytest.mark.parametrize("expression", ["1/0", "5 % 0", "7 // 0", "0 ** -1"])
def test_evaluate_division_by_zero(expression):
    with pytest.raises(DivisionByZero):
        evaluate(expression)


def test_evaluate_invalid_syntax_is_not_arithmetic():
    with pytest.raises(NotArithmetic):
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

    with pytest.raises(NotArithmetic):
        evaluate(expression)


def test_evaluate_rejects_huge_power_exponent():
    """2 ** 10_000_000 без ограничения кладёт CPU/память одним сообщением -
    регрессия на случай, если лимит будет случайно убран."""

    with pytest.raises(ResultTooBig):
        evaluate("2 ** 10000000")


@pytest.mark.parametrize(
    "expression",
    [
        "(9**1000)**1000",  # 3 млн бит: в сообщение не влезет
        "((9**1000)**1000)**1000",  # без проверки размера — минуты в event loop
        "9**1000 * 9**1000 * 9**1000 * 9**1000 * 9**1000",
        "1e308 * 10",  # float уходит в inf, а не в OverflowError
        "10.0 ** 400",  # а здесь OverflowError
    ],
)
def test_evaluate_rejects_results_too_big_for_a_message(expression):
    started = time.monotonic()
    with pytest.raises(ResultTooBig):
        evaluate(expression)
    assert time.monotonic() - started < 1, "размер должен проверяться до вычисления"


def test_evaluate_allows_big_results_that_fit_a_message():
    assert evaluate("2**1000") == 2**1000


# --- require_operator (пассивный триггер в чате, fun_router.py) --------------


# Правило владельца: считать, только если есть оператор между хотя бы двумя числами.
@pytest.mark.parametrize("expression", ["5", "-5", "+5", " 42 ", "-2", "+7999", "--2"])
def test_require_operator_rejects_bare_numbers(expression):
    with pytest.raises(NotArithmetic):
        evaluate(expression, require_operator=True)


@pytest.mark.parametrize(
    "expression,expected",
    [("2+2", 4), ("-(2+3)", -5), ("(2+2)*10", 40), ("2**10", 1024), ("-2-2", -4), ("1/2", 0.5)],
)
def test_require_operator_allows_real_expressions(expression, expected):
    assert evaluate(expression, require_operator=True) == expected


def test_require_operator_false_by_default_still_allows_bare_numbers():
    """require_operator по умолчанию False - явная команда "посчитай"
    (если она вообще где-то останется) не должна внезапно сломаться на
    голых числах."""

    assert evaluate("5") == 5
