# pragma version 0.4.3

from ethereum.ercs import IERC20


event AddLiquidity:
    provider: indexed(address)
    amounts: uint256[2]
    donation: bool


coins: public(immutable(address[2]))
last_amounts: public(uint256[2])
last_provider: public(address)
last_donation: public(bool)


@deploy
def __init__(_coins: address[2]):
    coins = _coins


@external
def add_liquidity(
    amounts: uint256[2],
    min_mint_amount: uint256,
    receiver: address,
    donation: bool,
) -> uint256:
    for i: uint256 in range(2):
        if amounts[i] > 0:
            assert extcall IERC20(coins[i]).transferFrom(msg.sender, self, amounts[i]), "transfer failed"

    self.last_amounts = amounts
    self.last_provider = msg.sender
    self.last_donation = donation
    log AddLiquidity(provider=msg.sender, amounts=amounts, donation=donation)

    return amounts[0] + amounts[1]
