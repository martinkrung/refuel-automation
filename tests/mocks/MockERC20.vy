# pragma version 0.4.3

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256


name: public(String[64])
symbol: public(String[32])
decimals: public(uint8)

totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])


@deploy
def __init__(_name: String[64], _symbol: String[32], _decimals: uint8):
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals


@external
def mint(_to: address, _amount: uint256):
    self.balanceOf[_to] += _amount
    self.totalSupply += _amount
    log Transfer(sender=empty(address), receiver=_to, value=_amount)


@external
def approve(_spender: address, _amount: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _amount
    log Approval(owner=msg.sender, spender=_spender, value=_amount)
    return True


@external
def transfer(_to: address, _amount: uint256) -> bool:
    self.balanceOf[msg.sender] -= _amount
    self.balanceOf[_to] += _amount
    log Transfer(sender=msg.sender, receiver=_to, value=_amount)
    return True


@external
def transferFrom(_from: address, _to: address, _amount: uint256) -> bool:
    allowed: uint256 = self.allowance[_from][msg.sender]
    if allowed != max_value(uint256):
        self.allowance[_from][msg.sender] = allowed - _amount
    self.balanceOf[_from] -= _amount
    self.balanceOf[_to] += _amount
    log Transfer(sender=_from, receiver=_to, value=_amount)
    return True
