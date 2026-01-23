import boa
import pytest


pytestmark = pytest.mark.ignore_isolation


def _fund_and_approve(token, owner, spender, amount):
    boa.deal(token, owner, amount, adjust_supply=False)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_create_stream_records_pool_and_coins(donation_streamer, pool_contract, tokens, donor):
    token0, token1 = tokens
    amounts = [10**18, 2 * 10**18]
    reward = 10**14
    period_length = 60

    _fund_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _fund_and_approve(token1, donor, donation_streamer.address, amounts[1])
    boa.env.set_balance(donor, reward)

    with boa.env.prank(donor):
        stream_id = donation_streamer.create_stream(
            pool_contract.address,
            [token0.address, token1.address],
            amounts,
            period_length,
            1,
            reward,
            value=reward,
        )

    stream = donation_streamer.streams(stream_id)
    assert stream[1] == pool_contract.address
    assert stream[2][0] == token0.address
    assert stream[2][1] == token1.address


def test_create_stream_refunds_excess_reward(donation_streamer, pool_contract, tokens, donor):
    token0, token1 = tokens
    amounts = [10**18, 2 * 10**18]
    reward_per_period = 10**14
    n_periods = 2
    reward_total = reward_per_period * n_periods
    reward_value = reward_total + 1

    _fund_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _fund_and_approve(token1, donor, donation_streamer.address, amounts[1])
    boa.env.set_balance(donor, reward_value)
    donor_balance = boa.env.get_balance(donor)

    with boa.env.prank(donor):
        donation_streamer.create_stream(
            pool_contract.address,
            [token0.address, token1.address],
            amounts,
            60,
            n_periods,
            reward_per_period,
            value=reward_value,
        )

    assert boa.env.get_balance(donor) == donor_balance - reward_total
