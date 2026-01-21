import boa
import pytest


pytestmark = pytest.mark.ignore_isolation


def _fund_and_approve(token, owner, spender, amount):
    boa.deal(token, owner, amount, adjust_supply=False)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_streams_due_are_due(donation_pool, tokens, donor):
    token0, token1 = tokens
    period_length = 60
    reward_per_period = 10**14

    for i in range(3):
        amounts = [10**18 + i, 2 * 10**18 + i]
        _fund_and_approve(token0, donor, donation_pool.address, amounts[0])
        _fund_and_approve(token1, donor, donation_pool.address, amounts[1])
        boa.env.set_balance(donor, reward_per_period)
        with boa.env.prank(donor):
            donation_pool.create_stream(
                amounts,
                period_length,
                1,
                reward_per_period,
                value=reward_per_period,
            )

    boa.env.time_travel(seconds=period_length)
    due_ids = donation_pool.streams_due(2)

    assert due_ids == [2, 1]
    for stream_id in due_ids:
        assert donation_pool.is_due(stream_id)
