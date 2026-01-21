import boa
import pytest


@pytest.fixture(autouse=True)
def _fast_mode():
    boa.env.enable_fast_mode()


@pytest.fixture()
def deployer():
    return boa.env.generate_address()


@pytest.fixture()
def donor():
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 10**21)
    return addr


@pytest.fixture()
def caller():
    addr = boa.env.generate_address()
    boa.env.set_balance(addr, 0)
    return addr


@pytest.fixture()
def tokens(deployer):
    with boa.env.prank(deployer):
        token0 = boa.load("tests/mocks/MockERC20.vy", "Token0", "TK0", 18)
        token1 = boa.load("tests/mocks/MockERC20.vy", "Token1", "TK1", 18)
    return token0, token1


@pytest.fixture()
def mock_pool(deployer, tokens):
    token0, token1 = tokens
    with boa.env.prank(deployer):
        return boa.load("tests/mocks/MockPool.vy", [token0.address, token1.address])


@pytest.fixture()
def donation_pool(deployer, mock_pool, tokens):
    token0, token1 = tokens
    with boa.env.prank(deployer):
        return boa.load("contracts/DonationPool.vy", mock_pool.address, [token0.address, token1.address])


@pytest.fixture()
def donation_pool_impl(deployer):
    with boa.env.prank(deployer):
        return boa.load_partial("contracts/DonationPool.vy").deploy_as_blueprint()


@pytest.fixture()
def donation_pool_interface():
    return boa.load_partial("contracts/DonationPool.vy")


@pytest.fixture()
def donation_factory(deployer, donation_pool_impl):
    with boa.env.prank(deployer):
        return boa.load("contracts/DonationFactory.vy", donation_pool_impl.address)
