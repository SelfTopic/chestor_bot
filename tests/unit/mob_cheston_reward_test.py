from src.bot.game_configs import MOB_CONFIG, STAT_UPGRADE_CONFIG, stat_cap_for_level


def _expected_range(level: int) -> tuple[int, int]:
    floor = stat_cap_for_level(level - 1, MOB_CONFIG.cheston_reward_reference_stat)
    ceiling = stat_cap_for_level(level, MOB_CONFIG.cheston_reward_reference_stat)
    reference_stat = (floor + ceiling) // 2
    price = STAT_UPGRADE_CONFIG.price(reference_stat, 1, MOB_CONFIG.cheston_reward_reference_stat)
    return (
        round(price * MOB_CONFIG.cheston_reward_multiplier_min),
        round(price * MOB_CONFIG.cheston_reward_multiplier_max),
    )


def test_cheston_reward_for_mob_win_stays_within_the_configured_multiplier_range():
    for level in (1, 2, 5, 10, 20, 50):
        low, high = _expected_range(level)
        for _ in range(50):
            reward = MOB_CONFIG.cheston_reward_for_mob_win(level)
            assert low <= reward <= high


def test_cheston_reward_for_mob_win_grows_with_level():
    # ECONOMY.md часть 4 - награда привязана к уровню (как LEVEL_UP_CONFIG),
    # а не фиксированное число - выше уровень должен стабильно давать больше.
    low_level_rewards = [MOB_CONFIG.cheston_reward_for_mob_win(1) for _ in range(30)]
    high_level_rewards = [MOB_CONFIG.cheston_reward_for_mob_win(20) for _ in range(30)]

    assert max(low_level_rewards) < min(high_level_rewards)


def test_cheston_reward_for_mob_win_is_positive_even_at_level_one():
    for _ in range(50):
        assert MOB_CONFIG.cheston_reward_for_mob_win(1) > 0
