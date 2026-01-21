# pragma version 0.4.3
"""
@title DonationFactory
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2025 - all rights reserved
@notice Permissionless deployer and registry for per-pool DonationPool contracts.
"""

event DonationPoolDeployed:
    pool: address
    donation_pool: address
    coins: address[N_COINS]
    deployer: address


N_COINS: constant(uint256) = 2
MAX_POOLS: constant(uint256) = 4294967296

donation_implementation: public(immutable(address))

pool_to_donation: public(HashMap[address, address])
donation_pools: public(DynArray[address, MAX_POOLS])


@deploy
def __init__(_implementation: address):
    assert _implementation != empty(address), "implementation required"
    donation_implementation = _implementation


@external
def deploy_donation_pool(_pool: address, _coins: address[N_COINS]) -> address:
    assert _pool != empty(address), "pool required"
    assert _coins[0] != empty(address) and _coins[1] != empty(address), "coin required"
    assert _coins[0] != _coins[1], "same coin"
    assert self.pool_to_donation[_pool] == empty(address), "pool exists"

    donation_pool: address = create_from_blueprint(
        donation_implementation,
        _pool,
        _coins,
        code_offset=3,
    )

    self.pool_to_donation[_pool] = donation_pool
    self.donation_pools.append(donation_pool)

    log DonationPoolDeployed(
        pool=_pool,
        donation_pool=donation_pool,
        coins=_coins,
        deployer=msg.sender,
    )

    return donation_pool


@view
@external
def donation_pool_count() -> uint256:
    return len(self.donation_pools)
