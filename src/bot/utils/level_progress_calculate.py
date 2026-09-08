"""Расчёт level_progress, см. BATTLE_DESIGN.md ("Формула левел-апа").

level_progress - 0-100%, без округлений, НЕ exp. Чистая функция здесь не
знает ничего о наградах/уведомлениях - это забота LevelUpService."""


def apply_level_progress(current_progress: float, delta: float) -> tuple[float, int]:
    """Возвращает (новый_progress, сколько_левел_апов).

    Заворачивается через 100% - большой прирост за один раз может дать сразу
    несколько уровней (см. "принятая эмерджентная механика": проигрыш
    слабому фарм-аккаунту при большом k). Не уходит ниже 0% - убыль
    прогресса НЕ откатывает уровень назад, левел-даун этой функцией не
    поддерживается и не планируется."""

    progress = current_progress + delta
    levels_gained = 0

    while progress >= 100:
        progress -= 100
        levels_gained += 1

    if progress < 0:
        progress = 0.0

    return progress, levels_gained
