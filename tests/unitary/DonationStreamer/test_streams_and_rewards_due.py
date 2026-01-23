import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_streams_and_rewards_due_orders_latest_first(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    period_length = 4
    rewards = [5, 7, 9]

    for i, reward in enumerate(rewards):
        amounts = [100 + i, 200 + i]
        _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
        _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])
        boa.env.set_balance(donor, reward)
        with boa.env.prank(donor):
            donation_streamer.create_stream(
                mock_pool.address,
                [token0.address, token1.address],
                amounts,
                period_length,
                1,
                reward,
                value=reward,
            )

    boa.env.time_travel(seconds=period_length)
    due_ids, due_rewards = donation_streamer.streams_and_rewards_due()
    assert due_ids == [2, 1, 0]
    assert due_rewards == [rewards[2], rewards[1], rewards[0]]


def test_streams_and_rewards_due_uses_remaining_on_final_period(
    donation_streamer, mock_pool, tokens, donor
):
    token0, token1 = tokens
    amounts = [100, 200]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    period_length = 4
    n_periods = 2
    reward_per_period = 5
    reward_total = reward_per_period * n_periods
    boa.env.set_balance(donor, reward_total)

    with boa.env.prank(donor):
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            period_length,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    boa.env.time_travel(seconds=period_length * n_periods)
    due_ids, due_rewards = donation_streamer.streams_and_rewards_due()
    assert due_ids == [0]
    assert due_rewards == [reward_total]


def test_streams_and_rewards_due_zero_liquidity_period_returns_reward(
    donation_streamer, mock_pool, tokens, donor
):
    token0, token1 = tokens
    amounts = [1, 1]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    reward_per_period = 5
    n_periods = 2
    reward_total = reward_per_period * n_periods
    boa.env.set_balance(donor, reward_total)

    with boa.env.prank(donor):
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            10,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    due_ids, due_rewards = donation_streamer.streams_and_rewards_due()
    assert due_ids == [0]
    assert due_rewards == [reward_per_period]
