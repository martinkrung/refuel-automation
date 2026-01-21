import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_cancel_stream_refunds(donation_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [1_000, 2_000]
    _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
    _mint_and_approve(token1, donor, donation_pool.address, amounts[1])

    period_length = 10
    n_periods = 3
    reward_per_period = 7
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

    donor_balance = boa.env.get_balance(donor)
    with boa.env.prank(donor):
        donation_pool.cancel_stream(0)

    assert token0.balanceOf(donor) == amounts[0]
    assert token1.balanceOf(donor) == amounts[1]
    assert boa.env.get_balance(donor) == donor_balance + reward_total

    stream = donation_pool.streams(0)
    assert stream[0] == boa.eval("empty(address)")
