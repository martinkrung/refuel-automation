import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_view_executable_matches_streams_due(donation_streamer, mock_pool, tokens, donor):
    token0, token1 = tokens
    period_length = 7

    for i in range(2):
        amounts = [100 + i, 200 + i]
        _mint_and_approve(token0, donor, donation_streamer.address, amounts[0])
        _mint_and_approve(token1, donor, donation_streamer.address, amounts[1])
        boa.env.set_balance(donor, 10)
        with boa.env.prank(donor):
            donation_streamer.create_stream(
                mock_pool.address,
                [token0.address, token1.address],
                amounts,
                period_length,
                1,
                10,
                value=10,
            )

    boa.env.time_travel(seconds=period_length)
    due_ids = donation_streamer.streams_due(2)
    assert donation_streamer.view_executable(2) == due_ids
