import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_execute_one_sends_tokens_and_reward(donation_pool, mock_pool, tokens, donor, caller):
    token0, token1 = tokens
    amounts = [1_000, 2_000]
    _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
    _mint_and_approve(token1, donor, donation_pool.address, amounts[1])

    period_length = 10
    n_periods = 2
    reward_per_period = 50
    reward_total = reward_per_period * n_periods
    boa.env.set_balance(donor, reward_total)

    with boa.env.prank(donor):
        donation_pool.create_stream(
            amounts,
            period_length,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    boa.env.time_travel(seconds=period_length)
    caller_balance = boa.env.get_balance(caller)

    with boa.env.prank(caller):
        executed = donation_pool.execute_one(0)

    assert executed == 1
    assert boa.env.get_balance(caller) == caller_balance + reward_per_period
    assert token0.balanceOf(mock_pool.address) == amounts[0] // n_periods
    assert token1.balanceOf(mock_pool.address) == amounts[1] // n_periods

    stream = donation_pool.streams(0)
    assert stream[4] == n_periods - 1
