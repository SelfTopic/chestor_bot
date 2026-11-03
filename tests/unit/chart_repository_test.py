from src.bot.repositories import AbandonedMachine, ChartRepository, Refund, SettledBet

CHAT = -1001


async def test_one_open_machine_per_chat(session, make_user):
    await make_user(telegram_id=1)
    charts = ChartRepository(session)

    first = await charts.open_machine(CHAT, opened_by=1)
    assert first is not None
    assert await charts.open_machine(CHAT, opened_by=1) is None
    assert await charts.open_machine(CHAT - 1, opened_by=1) is not None

    await charts.close_machine(first)
    assert await charts.open_machine(CHAT, opened_by=1) is not None


async def test_refunds_unsettled_bets_not_cashed_out(session, make_user):
    for telegram_id in (1, 2, 3):
        await make_user(telegram_id=telegram_id, username=None)
    charts = ChartRepository(session)
    machine = await charts.open_machine(CHAT, opened_by=1)
    assert machine is not None
    await charts.set_message(machine, 77)

    settled = await charts.start_round(machine, crash=241)
    await charts.add_bet(settled, 1, 1000, None)
    await charts.settle_round(settled, [SettledBet(1, None, 0)])
    current = await charts.start_round(machine, crash=500)
    await charts.add_bet(current, 2, 1000, None)
    await charts.add_bet(current, 3, 3000, 200)
    await charts.cash_out(current, 2, 150, 1500)

    assert await charts.abandoned_machines() == [AbandonedMachine(machine, CHAT, 77)]
    assert await charts.refunds(machine) == [Refund(3, 3000)]

    await charts.abandon_rounds(machine)
    await charts.close_machine(machine)
    assert await charts.refunds(machine) == []
    assert await charts.abandoned_machines() == []
