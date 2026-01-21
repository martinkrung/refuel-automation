import boa


def test_deploy_donation_pool(donation_factory, donation_pool_interface, mock_pool, tokens):
    token0, token1 = tokens
    pool_addr = donation_factory.deploy_donation_pool(
        mock_pool.address,
        [token0.address, token1.address],
    )
    assert pool_addr != boa.eval("empty(address)")
    assert donation_factory.pool_to_donation(mock_pool.address) == pool_addr

    donation_pool = donation_pool_interface.at(pool_addr)
    assert donation_pool.pool() == mock_pool.address
