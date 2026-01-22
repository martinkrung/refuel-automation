import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_execute_sends_tokens_and_reward(donation_streamer, mock_pool, tokens, donor, caller):
    token0, token1 = tokens
    amounts = [1_000, 2_000]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    period_length = 10
    n_periods = 2
    reward_per_period = 50
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

    caller_balance = boa.env.get_balance(caller)

    with boa.env.prank(caller):
        executed = donation_streamer.execute(0)

    assert executed == 1
    assert boa.env.get_balance(caller) == caller_balance + reward_per_period
    assert token0.balanceOf(mock_pool.address) == amounts[0] // n_periods
    assert token1.balanceOf(mock_pool.address) == amounts[1] // n_periods

    remaining0 = amounts[0] - amounts[0] // n_periods
    remaining1 = amounts[1] - amounts[1] // n_periods
    assert token0.allowance(donation_streamer.address, mock_pool.address) == remaining0
    assert token1.allowance(donation_streamer.address, mock_pool.address) == remaining1

    stream = donation_streamer.streams(0)
    assert stream[9] == n_periods - 1


def test_execute_sends_leftover_on_final_period(
    donation_streamer, mock_pool, tokens, donor, caller
):
    token0, token1 = tokens
    amounts = [5, 7]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    period_length = 10
    n_periods = 2
    reward_per_period = 3
    reward_total = reward_per_period * n_periods + 1
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

    pool_balance0 = token0.balanceOf(mock_pool.address)
    pool_balance1 = token1.balanceOf(mock_pool.address)

    caller_balance = boa.env.get_balance(caller)
    with boa.env.prank(caller):
        donation_streamer.execute(0)

    assert boa.env.get_balance(caller) == caller_balance + reward_per_period

    assert token0.balanceOf(mock_pool.address) == pool_balance0 + amounts[0] // n_periods
    assert token1.balanceOf(mock_pool.address) == pool_balance1 + amounts[1] // n_periods

    boa.env.time_travel(seconds=period_length)
    caller_balance = boa.env.get_balance(caller)
    with boa.env.prank(caller):
        donation_streamer.execute(0)

    assert boa.env.get_balance(caller) == caller_balance + (reward_total - reward_per_period)

    assert token0.balanceOf(mock_pool.address) == pool_balance0 + amounts[0]
    assert token1.balanceOf(mock_pool.address) == pool_balance1 + amounts[1]
    assert token0.allowance(donation_streamer.address, mock_pool.address) == 0
    assert token1.allowance(donation_streamer.address, mock_pool.address) == 0
