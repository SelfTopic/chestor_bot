"""routers/ghoul/evolution: "эволюция"/"мутация" открывают новый тип кагуне (всегда
следующий по лестнице укаку -> коукаку -> ринкаку -> бикаку, не выбор игрока) и
какуджу, за CheSton и RC одновременно. Меню - rich с кнопками; на сбой правки
reply_markup у запасного текста не теряется (answer_rich_or_text из routers/rich.py
этого не умеет, здесь свой путь)."""

from src.bot.config import game_config
from src.bot.dialogs import Dialogs
from src.bot.game_configs import EVOLUTION_CONFIG
from src.bot.types import KaguneType
from src.bot.utils import format_amount
from src.database.models import Ghoul

from .conftest import (
    button_data,
    callback_update,
    matches_phrase,
    message_update,
    only_text,
    rich_texts,
)
from .test_ghoul_routers import UID, balance_of, get_ghoul, seed_ghoul
from .test_common_routers import seed

EVOLUTION = Dialogs.kagune.evolution


async def _seed_one_type(session_factory, **extra) -> None:
    await seed(
        session_factory,
        UID,
        "Вася",
        balance=EVOLUTION_CONFIG.new_kagune_cheston + EVOLUTION_CONFIG.kakuja_cheston,
    )
    await seed_ghoul(
        session_factory,
        UID,
        kagune_type_bit=KaguneType.UKAKU.value["bit"],
        kagune_strength_ukaku=1,
        rc_money=EVOLUTION_CONFIG.new_kagune_rc + EVOLUTION_CONFIG.kakuja_rc,
        **extra,
    )


class TestEvolutionMenu:
    async def test_shows_status_and_both_buttons(self, feed, telegram, session_factory):
        await _seed_one_type(session_factory)

        telegram = await feed(message_update("эволюция", uid=UID))

        (body,) = telegram.bodies("sendRichMessage")
        texts = rich_texts(body)
        assert any("Укаку" in text for text in texts)
        assert only_text(EVOLUTION.not_owned()) in texts
        assert only_text(EVOLUTION.kakuja_no()) in texts

        assert button_data(body, only_text(EVOLUTION.buy_kagune_button(
            kagune="Коукаку",
            cheston=format_amount(EVOLUTION_CONFIG.new_kagune_cheston),
            rc=format_amount(EVOLUTION_CONFIG.new_kagune_rc),
        ))).startswith("evo_kagune:")
        assert button_data(body, only_text(EVOLUTION.buy_kakuja_button(
            cheston=format_amount(EVOLUTION_CONFIG.kakuja_cheston),
            rc=format_amount(EVOLUTION_CONFIG.kakuja_rc),
        ))).startswith("evo_kakuja:")

    async def test_mutation_is_the_same_menu(self, feed, telegram, session_factory):
        await _seed_one_type(session_factory)

        telegram = await feed(message_update("мутация", uid=UID))

        (body,) = telegram.bodies("sendRichMessage")
        assert any("Эволюция" in text for text in rich_texts(body))

    async def test_all_kagune_owned_hides_that_button(self, send, telegram, session_factory):
        await _seed_one_type(session_factory)
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=sum(t.value["bit"] for t in KaguneType),
            kagune_strength_ukaku=1,
            kagune_strength_koukaku=1,
            kagune_strength_rinkaku=1,
            kagune_strength_bikaku=1,
        )

        await send("эволюция", uid=UID)

        (body,) = telegram.bodies("sendRichMessage")
        assert "evo_kagune:" not in str(body.get("reply_markup"))

    async def test_already_kakuja_hides_that_button(self, send, telegram, session_factory):
        await _seed_one_type(session_factory, is_kakuja=True)

        await send("эволюция", uid=UID)

        (body,) = telegram.bodies("sendRichMessage")
        assert "evo_kakuja:" not in str(body.get("reply_markup"))


class TestBuyKagune:
    async def test_success_grants_next_type_on_the_ladder(
        self, feed, telegram, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await _seed_one_type(session_factory)
        balance_before = await balance_of(session_factory, UID)

        telegram = await feed(callback_update(f"evo_kagune:{UID}", uid=UID))

        assert telegram.methods_called("deleteMessage") == 1
        (body,) = telegram.bodies("sendMessage")
        assert matches_phrase(body["text"], "kagune.evolution.kagune_done")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert set(ghoul_owned_types(ghoul)) == {KaguneType.UKAKU, KaguneType.KOUKAKU}
        assert ghoul.kagune_strength_koukaku == 1

        balance_after = await balance_of(session_factory, UID)
        assert balance_before - balance_after == EVOLUTION_CONFIG.new_kagune_cheston
        assert ghoul.rc_money == EVOLUTION_CONFIG.kakuja_rc  # потрачен только за кагуне

    async def test_not_enough_cheston_keeps_state_and_answers_with_alert(
        self, feed, telegram, session_factory
    ):
        await _seed_one_type(session_factory)
        await seed(session_factory, UID, "Вася", balance=0)

        telegram = await feed(callback_update(f"evo_kagune:{UID}", uid=UID))

        assert telegram.methods_called("deleteMessage") == 0
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert matches_phrase(answer["text"], "errors.not_enough_money")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_koukaku is None

    async def test_not_enough_rc_keeps_state_and_answers_with_alert(
        self, feed, telegram, session_factory
    ):
        await _seed_one_type(session_factory)
        await seed_ghoul(session_factory, UID, rc_money=0)

        telegram = await feed(callback_update(f"evo_kagune:{UID}", uid=UID))

        assert telegram.methods_called("deleteMessage") == 0
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert matches_phrase(answer["text"], "errors.not_enough_rc")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_koukaku is None


class TestBecomeKakuja:
    async def test_success_sets_the_flag(
        self, feed, telegram, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await _seed_one_type(session_factory)
        balance_before = await balance_of(session_factory, UID)

        telegram = await feed(callback_update(f"evo_kakuja:{UID}", uid=UID))

        assert telegram.methods_called("deleteMessage") == 1
        (body,) = telegram.bodies("sendMessage")
        assert matches_phrase(body["text"], "kagune.evolution.kakuja_done")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.is_kakuja is True

        balance_after = await balance_of(session_factory, UID)
        assert balance_before - balance_after == EVOLUTION_CONFIG.kakuja_cheston
        assert ghoul.rc_money == EVOLUTION_CONFIG.new_kagune_rc  # потрачен только за какуджу

    async def test_already_kakuja_answers_with_alert(self, feed, telegram, session_factory):
        await _seed_one_type(session_factory, is_kakuja=True)

        telegram = await feed(callback_update(f"evo_kakuja:{UID}", uid=UID))

        assert telegram.methods_called("deleteMessage") == 0
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert matches_phrase(answer["text"], "kagune.evolution.already_kakuja")


def ghoul_owned_types(ghoul: Ghoul) -> list[KaguneType]:
    return [
        kagune_type
        for kagune_type in KaguneType
        if getattr(ghoul, kagune_type.value["strength_column"]) is not None
    ]
