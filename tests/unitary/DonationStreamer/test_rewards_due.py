import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_rewards_due_orders_from_end(donation_streamer, mock_pool, tokens, donor):
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
    due_rewards = donation_streamer.rewards_due([0, 1, 2], 2)
    assert due_rewards == [rewards[2], rewards[1]]


def test_rewards_due_uses_remaining_on_final_period(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [100, 200]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    period_length = 4
    n_periods = 2
    reward_per_period = 5
    reward_total = reward_per_period * n_periods + 3
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
    due_rewards = donation_streamer.rewards_due([0], 1)
    assert due_rewards == [reward_total]
