import boa
import pytest


pytestmark = pytest.mark.ignore_isolation


def test_pool_config(donation_pool, pool_address, pool_contract):
    zero_address = boa.eval("empty(address)")
    pool = donation_pool.pool()
    coin0 = donation_pool.coins(0)
    coin1 = donation_pool.coins(1)

    assert pool == pool_address
    assert coin0 == pool_contract.coins(0)
    assert coin1 == pool_contract.coins(1)
    assert pool != zero_address
    assert coin0 != zero_address
    assert coin1 != zero_address
    assert coin0 != coin1
    assert boa.env.get_code(pool)
    assert boa.env.get_code(coin0)
    assert boa.env.get_code(coin1)
