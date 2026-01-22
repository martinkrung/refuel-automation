import boa
import pytest


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_create_stream_records_and_transfers(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [1_000, 2_000]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    period_length = 10
    n_periods = 4
    reward_per_period = 25
    reward_total = reward_per_period * n_periods
    boa.env.set_balance(donor, reward_total)
    now = boa.env.timestamp

    with boa.env.prank(donor):
        stream_id = donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            period_length,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    assert stream_id == 0
    assert donation_streamer.stream_count() == 1
    stream = donation_streamer.streams(stream_id)
    assert stream[0] == donor
    assert stream[1] == mock_pool.address
    assert stream[2][0] == token0.address
    assert stream[2][1] == token1.address
    assert stream[3][0] == amounts[0] // n_periods
    assert stream[3][1] == amounts[1] // n_periods
    assert stream[4] == period_length
    assert stream[5] == reward_per_period
    assert stream[6] == now
    assert stream[7] == reward_total
    assert stream[8][0] == amounts[0]
    assert stream[8][1] == amounts[1]
    assert stream[9] == n_periods

    assert token0.allowance(donation_streamer.address, mock_pool.address) == amounts[0]
    assert token1.allowance(donation_streamer.address, mock_pool.address) == amounts[1]

    assert token0.balanceOf(donation_streamer.address) == amounts[0]
    assert token1.balanceOf(donation_streamer.address) == amounts[1]
    assert boa.env.get_balance(donation_streamer.address) == reward_total


def test_create_stream_accumulates_allowance(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    amounts_a = [100, 200]
    amounts_b = [300, 400]
    total0 = amounts_a[0] + amounts_b[0]
    total1 = amounts_a[1] + amounts_b[1]
    token0.mint(donor, total0)
    token1.mint(donor, total1)

    with boa.env.prank(donor):
        token0.approve(donation_streamer.address, total0)
        token1.approve(donation_streamer.address, total1)

    boa.env.set_balance(donor, 2)
    with boa.env.prank(donor):
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts_a,
            10,
            1,
            1,
            value=1,
        )

    assert token0.allowance(donation_streamer.address, mock_pool.address) == amounts_a[0]
    assert token1.allowance(donation_streamer.address, mock_pool.address) == amounts_a[1]

    with boa.env.prank(donor):
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts_b,
            10,
            1,
            1,
            value=1,
        )

    assert token0.allowance(donation_streamer.address, mock_pool.address) == total0
    assert token1.allowance(donation_streamer.address, mock_pool.address) == total1


def test_create_stream_requires_value(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [100, 200]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    with boa.env.prank(donor), boa.reverts():
        donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            10,
            2,
            5,
            value=5,
        )


def test_create_stream_tracks_reward_remaining(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [100, 200]
    _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
    _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])

    reward_per_period = 5
    n_periods = 2
    reward_total = reward_per_period * n_periods + 4
    boa.env.set_balance(donor, reward_total)

    with boa.env.prank(donor):
        stream_id = donation_streamer.create_stream(
            mock_pool.address,
            [token0.address, token1.address],
            amounts,
            10,
            n_periods,
            reward_per_period,
            value=reward_total,
        )

    stream = donation_streamer.streams(stream_id)
    assert stream[7] == reward_total


def test_create_stream_checks_pool_coins(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    amounts = [100, 200]
    reward_total = 10
    boa.env.set_balance(donor, reward_total)

    with boa.env.prank(donor), boa.reverts():
        donation_streamer.create_stream(
            mock_pool.address,
            [token1.address, token0.address],
            amounts,
            10,
            1,
            reward_total,
            value=reward_total,
        )
