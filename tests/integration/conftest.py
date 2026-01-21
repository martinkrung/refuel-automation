import os
from pathlib import Path

import boa
import pytest


DEFAULT_POOL_ADDRESS = "0x027B40F5917FCd0eac57d7015e120096A5F92ca9"
DEFAULT_FORK_BLOCK = 24_280_000

POOL_ABI_UINT = """
[
  {
    "name": "coins",
    "type": "function",
    "inputs": [{"name": "i", "type": "uint256"}],
    "outputs": [{"name": "", "type": "address"}],
    "stateMutability": "view"
  }
]
"""

POOL_ABI_INT = """
[
  {
    "name": "coins",
    "type": "function",
    "inputs": [{"name": "i", "type": "int128"}],
    "outputs": [{"name": "", "type": "address"}],
    "stateMutability": "view"
  }
]
"""

ERC20_ABI = """
[
  {
    "name": "balanceOf",
    "type": "function",
    "inputs": [{"name": "account", "type": "address"}],
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view"
  },
  {
    "name": "totalSupply",
    "type": "function",
    "inputs": [],
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view"
  },
  {
    "name": "allowance",
    "type": "function",
    "inputs": [
      {"name": "owner", "type": "address"},
      {"name": "spender", "type": "address"}
    ],
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view"
  },
  {
    "name": "approve",
    "type": "function",
    "inputs": [
      {"name": "spender", "type": "address"},
      {"name": "amount", "type": "uint256"}
    ],
    "outputs": [{"name": "", "type": "bool"}],
    "stateMutability": "nonpayable"
  }
]
"""


def _read_env_file() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        if not sep:
            continue
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@pytest.fixture(scope="session")
def rpc_url():
    rpc = os.getenv("RPC_URL")
    if not rpc:
        rpc = _read_env_file().get("RPC_URL")
    if rpc:
        return rpc
    key = os.getenv("DRPC_API_KEY")
    if not key:
        key = _read_env_file().get("DRPC_API_KEY")
    if key:
        return f"https://lb.drpc.org/ogrpc?network=ethereum&dkey={key}"
    return None


@pytest.fixture(scope="session")
def fork_block():
    block = os.getenv("FORK_BLOCK")
    if not block:
        block = _read_env_file().get("FORK_BLOCK")
    if block:
        return int(block, 0)
    return DEFAULT_FORK_BLOCK


@pytest.fixture(scope="session")
def pool_address():
    address = os.getenv("POOL_ADDRESS")
    if not address:
        address = _read_env_file().get("POOL_ADDRESS")
    if not address:
        address = os.getenv("TARGET_POOL_ADDRESS")
    if not address:
        address = _read_env_file().get("TARGET_POOL_ADDRESS")
    if not address:
        address = os.getenv("DONATION_POOL_ADDRESS")
    if not address:
        address = _read_env_file().get("DONATION_POOL_ADDRESS")
    return address or DEFAULT_POOL_ADDRESS


@pytest.fixture()
def forked_env(rpc_url, fork_block):
    if not rpc_url:
        pytest.skip("RPC_URL or DRPC_API_KEY required for fork tests")
    with boa.fork(url=rpc_url, block_identifier=fork_block):
        boa.env.enable_fast_mode()
        yield


@pytest.fixture()
def deployer(forked_env):
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**20)
    return addr


@pytest.fixture()
def donor(forked_env):
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**21)
    return addr


@pytest.fixture()
def caller(forked_env):
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 0)
    return addr


@pytest.fixture()
def pool_contract(forked_env, pool_address):
    if not boa.env.get_code(pool_address):
        pytest.skip("Pool not deployed at fork block")

    factory_uint = boa.loads_abi(POOL_ABI_UINT, name="CurvePoolUint")
    contract = factory_uint.at(pool_address)
    try:
        contract.coins(0)
        return contract
    except Exception:
        factory_int = boa.loads_abi(POOL_ABI_INT, name="CurvePoolInt")
        contract = factory_int.at(pool_address)
        contract.coins(0)
        return contract


@pytest.fixture(scope="session")
def erc20_factory():
    return boa.loads_abi(ERC20_ABI, name="ERC20")


@pytest.fixture()
def tokens(pool_contract, erc20_factory):
    token0 = erc20_factory.at(pool_contract.coins(0))
    token1 = erc20_factory.at(pool_contract.coins(1))
    return token0, token1


@pytest.fixture()
def donation_pool(deployer, pool_contract, tokens):
    token0, token1 = tokens
    with boa.env.prank(deployer):
        return boa.load("contracts/DonationPool.vy", pool_contract.address, [token0.address, token1.address])
