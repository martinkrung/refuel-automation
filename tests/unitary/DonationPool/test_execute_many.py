import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_execute_many_aggregates_rewards(donation_pool, tokens, donor, caller):
    token0, token1 = tokens
    reward_total = 0
    period_length = 7

    for i in range(2):
        amounts = [1_000 + i, 2_000 + i]
        _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
        _mint_and_approve(token1, donor, donation_pool.address, amounts[1])
        reward_per_period = 10 + i
        reward_total += reward_per_period
        boa.env.set_balance(donor, reward_total)
        with boa.env.prank(donor):
            donation_pool.create_stream(
                amounts,
                period_length,
                1,
                reward_per_period,
                value=reward_per_period,
            )

    boa.env.time_travel(seconds=period_length)
    caller_balance = boa.env.get_balance(caller)

    with boa.env.prank(caller):
        executed = donation_pool.execute_many([0, 1])

    assert executed == 2
    assert boa.env.get_balance(caller) == caller_balance + reward_total
