import boa
import pytest


pytestmark = pytest.mark.ignore_isolation


def _fund_and_approve(token, owner, spender, amount):
    boa.deal(token, owner, amount, adjust_supply=False)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_execute_adds_liquidity_and_pays_reward(
    donation_streamer, pool_contract, tokens, donor, caller
):
    token0, token1 = tokens
    period_length = 120
    n_periods = 2
    reward_per_period = 10**14
    reward_total = reward_per_period * n_periods
    amounts = [2 * 10**18, 4 * 10**18]

    _fund_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _fund_and_approve(token1, donor, donation_streamer.address, amounts[1])
    boa.env.set_balance(donor, reward_total + 10**18)
    donor_balance_before = boa.env.get_balance(donor)

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

    assert stream_id == 0
    assert boa.env.get_balance(donor) == donor_balance_before - reward_total

    pool_balance0_before = token0.balanceOf(pool_contract.address)
    pool_balance1_before = token1.balanceOf(pool_contract.address)
    caller_balance_before = boa.env.get_balance(caller)

    with boa.env.prank(caller):
        executed = donation_streamer.execute(stream_id)

    assert executed == 1
    assert boa.env.get_balance(caller) == caller_balance_before + reward_per_period
    assert token0.balanceOf(pool_contract.address) == pool_balance0_before + amounts[0] // n_periods
    assert token1.balanceOf(pool_contract.address) == pool_balance1_before + amounts[1] // n_periods
