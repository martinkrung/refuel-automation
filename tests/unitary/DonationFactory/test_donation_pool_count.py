def test_donation_pool_count(donation_factory, mock_pool, tokens):
    token0, token1 = tokens
    donation_factory.deploy_donation_pool(
        mock_pool.address,
        [token0.address, token1.address],
    )
    assert donation_factory.donation_pool_count() == 1
