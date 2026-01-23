import boa
import pytest


pytestmark = pytest.mark.ignore_isolation


def _fund_and_approve(token, owner, spender, amount):
    boa.deal(token, owner, amount, adjust_supply=False)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_cancel_stream_refunds_remaining(donation_streamer, pool_contract, tokens, donor, caller):
    token0, token1 = tokens
    period_length = 120
    n_periods = 2
    reward_per_period = 10**14
    reward_total = reward_per_period * n_periods
    amounts = [2 * 10**18, 4 * 10**18]

    _fund_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _fund_and_approve(token1, donor, donation_streamer.address, amounts[1])
    boa.env.set_balance(donor, reward_total + 10**18)

    with boa.env.prank(donor):
        stream_id = donation_streamer.create_stream(
            pool_contract.address,
            [token0.address, token1.address],
            amounts,
            period_length,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    with boa.env.prank(caller):
        donation_streamer.execute(stream_id)

    donor_balance_before = boa.env.get_balance(donor)
    with boa.env.prank(donor):
        donation_streamer.cancel_stream(stream_id)

    assert token0.balanceOf(donor) == amounts[0] // n_periods
    assert token1.balanceOf(donor) == amounts[1] // n_periods
    assert boa.env.get_balance(donor) == donor_balance_before + (reward_total - reward_per_period)
    assert token0.allowance(donation_streamer.address, pool_contract.address) == 0
    assert token1.allowance(donation_streamer.address, pool_contract.address) == 0

    stream = donation_streamer.streams(stream_id)
    assert stream[0] == boa.eval("empty(address)")
