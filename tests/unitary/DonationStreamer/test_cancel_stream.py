import boa
import pytest


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


@pytest.mark.parametrize("amounts", ([1_000, 2_000], [0, 2_000], [1_000, 0]))
def test_cancel_stream_refunds(donation_streamer, mock_pool, tokens, donor, amounts):
    token0, token1 = tokens
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    period_length = 10
    n_periods = 3
    reward_per_period = 7
    reward_total = reward_per_period * n_periods
    boa.env.set_balance(donor, reward_total)

    with boa.env.prank(donor):
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            period_length,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    donor_balance = boa.env.get_balance(donor)
    with boa.env.prank(donor):
        donation_streamer.cancel_stream(0)

    assert token0.balanceOf(donor) == amounts[0]
    assert token1.balanceOf(donor) == amounts[1]
    assert boa.env.get_balance(donor) == donor_balance + reward_total
    assert token0.allowance(donation_streamer.address, mock_pool.address) == 0
    assert token1.allowance(donation_streamer.address, mock_pool.address) == 0

    stream = donation_streamer.streams(0)
    assert stream[0] == boa.eval("empty(address)")


def test_cancel_stream_requires_donor(donation_streamer, mock_pool, tokens, donor, caller):
    token0, token1 = tokens
    amounts = [1_000, 2_000]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    reward_total = 9
    boa.env.set_balance(donor, reward_total)
    with boa.env.prank(donor):
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            10,
            1,
            reward_total,
            value=reward_total,
        )

    with boa.env.prank(caller), boa.reverts():
        donation_streamer.cancel_stream(0)
