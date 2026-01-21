import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_is_due_tracks_schedule(donation_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [100, 200]
    _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
    _mint_and_approve(token1, donor, donation_pool.address, amounts[1])

    period_length = 5
    reward_per_period = 3
    boa.env.set_balance(donor, reward_per_period)
    with boa.env.prank(donor):
        donation_pool.create_stream(
            amounts,
            period_length,
            1,
            reward_per_period,
            value=reward_per_period,
        )

    assert donation_pool.is_due(0) is False
    boa.env.time_travel(seconds=period_length)
    assert donation_pool.is_due(0) is True
