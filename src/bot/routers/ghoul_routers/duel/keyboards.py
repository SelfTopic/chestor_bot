"""Inline-клавиатуры дуэли - чистые функции без побочных эффектов, чтобы
роутерам/фоновым таймаутам не приходилось верстать разметку inline."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def consent_keyboard(duel_id: int, initiator_id: int, target_id: int) -> InlineKeyboardMarkup:
    """Две ОТДЕЛЬНЫЕ кнопки - сама команда "дуэль" ещё не согласие, нужно
    явное подтверждение обеих сторон (см. чат)."""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтверждаю вызов (инициатор)",
                    callback_data=f"duel:{duel_id}:consent_initiator:{initiator_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ Принимаю бой",
                    callback_data=f"duel:{duel_id}:consent_target:{target_id}",
                )
            ],
        ]
    )


def fora_keyboard(duel_id: int, favored_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ Всерьёз", callback_data=f"duel:{duel_id}:fora_serious:{favored_id}"
                ),
                InlineKeyboardButton(
                    text="🤝 Дать фору",
                    callback_data=f"duel:{duel_id}:fora_handicap:{favored_id}",
                ),
            ]
        ]
    )


def outcome_keyboard(duel_id: int, winner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Ограбить", callback_data=f"duel:{duel_id}:outcome_rob:{winner_id}"
                ),
                InlineKeyboardButton(
                    text="🕊️ Отпустить",
                    callback_data=f"duel:{duel_id}:outcome_release:{winner_id}",
                ),
                InlineKeyboardButton(
                    text="🍖 Съесть", callback_data=f"duel:{duel_id}:outcome_eat:{winner_id}"
                ),
            ]
        ]
    )


__all__ = ["consent_keyboard", "fora_keyboard", "outcome_keyboard"]
