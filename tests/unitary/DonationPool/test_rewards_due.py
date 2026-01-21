import boa


def _mint_and_approve(token, owner, spender, amount):
    token.mint(owner, amount)
    with boa.env.prank(owner):
        token.approve(spender, amount)


def test_rewards_due_orders_from_end(donation_pool, tokens, donor):
    token0, token1 = tokens
    period_length = 4
    rewards = [5, 7, 9]

    for i, reward in enumerate(rewards):
        amounts = [100 + i, 200 + i]
        _mint_and_approve(token0, donor, donation_pool.address, amounts[0])
        _mint_and_approve(token1, donor, donation_pool.address, amounts[1])
        boa.env.set_balance(donor, reward)
        with boa.env.prank(donor):
            donation_pool.create_stream(
                amounts,
                period_length,
                1,
                reward,
                value=reward,
            )

    boa.env.time_travel(seconds=period_length)
    due_rewards = donation_pool.rewards_due([0, 1, 2], 2)
    assert due_rewards == [rewards[2], rewards[1]]
