import boa
import pytest


pytestmark = pytest.mark.ignore_isolation


def _fund_and_approve(token, owner, spender, amount):
    boa.deal(token, owner, amount, adjust_supply=False)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def _due_periods(stream, now, zero_address):
    donor = stream[0]
    period_length = stream[4]
    periods_remaining = stream[9]
    next_ts = stream[6]

    if donor == zero_address:
        return 0
    if periods_remaining == 0 or period_length == 0:
        return 0
    if now < next_ts:
        return 0

    periods_due = (now - next_ts) // period_length + 1
    if periods_due > periods_remaining:
        periods_due = periods_remaining
    return periods_due


def test_streams_and_rewards_due_are_due(donation_streamer, pool_contract, tokens, donor):
    token0, token1 = tokens
    period_length = 60
    reward_per_period = 10**14

    for i in range(3):
        amounts = [10**18 + i, 2 * 10**18 + i]
        _fund_and_approve(token0, donor, donation_streamer.address, amounts[0])
        _fund_and_approve(token1, donor, donation_streamer.address, amounts[1])
        boa.env.set_balance(donor, reward_per_period)
        with boa.env.prank(donor):
            donation_streamer.create_stream(
                pool_contract.address,
                [token0.address, token1.address],
                amounts,
                period_length,
                1,
                reward_per_period,
                value=reward_per_period,
            )

    boa.env.time_travel(seconds=period_length)
    due_ids, rewards = donation_streamer.streams_and_rewards_due()

    assert due_ids == [2, 1, 0]
    assert rewards == [reward_per_period, reward_per_period, reward_per_period]


def test_streams_and_rewards_due_matches_periods(donation_streamer, pool_contract, tokens, donor):
    token0, token1 = tokens
    period_length = 60
    rewards = [10**14, 2 * 10**14, 3 * 10**14]

    for i, reward in enumerate(rewards):
        amounts = [10**18 + i, 2 * 10**18 + i]
        _fund_and_approve(token0, donor, donation_streamer.address, amounts[0])
        _fund_and_approve(token1, donor, donation_streamer.address, amounts[1])
        boa.env.set_balance(donor, reward * 3)
        with boa.env.prank(donor):
            donation_streamer.create_stream(
                pool_contract.address,
                [token0.address, token1.address],
                amounts,
                period_length,
                3,
                reward,
                value=reward * 3,
            )

    boa.env.time_travel(seconds=period_length * 2)
    due_ids, rewards_due = donation_streamer.streams_and_rewards_due()
    now = boa.env.timestamp
    zero_address = boa.eval("empty(address)")

    expected = []
    for stream_id in due_ids:
        stream = donation_streamer.streams(stream_id)
        expected.append(stream[5] * _due_periods(stream, now, zero_address))

    assert rewards_due == expected
