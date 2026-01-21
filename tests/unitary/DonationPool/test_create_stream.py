import boa
import pytest


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_create_stream_records_and_transfers(donation_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [1_000, 2_000]
    _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
    _mint_and_approve(token1, donor, donation_pool.address, amounts[1])

    period_length = 10
    n_periods = 4
    reward_per_period = 25
    reward_total = reward_per_period * n_periods
    boa.env.set_balance(donor, reward_total)
    now = boa.env.timestamp

    with boa.env.prank(donor):
        stream_id = donation_pool.create_stream(
            amounts,
            period_length,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    assert stream_id == 0
    assert donation_pool.stream_count() == 1
    stream = donation_pool.streams(stream_id)
    assert stream[0] == donor
    assert stream[1][0] == amounts[0]
    assert stream[1][1] == amounts[1]
    assert stream[2] == period_length
    assert stream[3] == n_periods
    assert stream[4] == now + period_length
    assert stream[5] == reward_per_period

    assert token0.balanceOf(donation_pool.address) == amounts[0]
    assert token1.balanceOf(donation_pool.address) == amounts[1]
    assert boa.env.get_balance(donation_pool.address) == reward_total


def test_create_stream_requires_value(donation_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [100, 200]
    _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
    _mint_and_approve(token1, donor, donation_pool.address, amounts[1])

    with boa.env.prank(donor), boa.reverts():
        donation_pool.create_stream(
            amounts,
            10,
            2,
            5,
            value=5,
        )
