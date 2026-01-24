import os

from eth_account import Account
from eth_utils import keccak, to_bytes, to_checksum_address

import boa
from boa.explorer import Etherscan

from secure_key_utils import decrypt_private_key, getpass


CREATE_X_ADDRESS = "0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed"
RPC_URL = "https://polygon.drpc.org"

CONTRACT_NAME = "DonationStreamer"
CONTRACT_PATH = "contracts/DonationStreamer.vy"
SALT_SEED_TEXT = "DonationStreamer:v0.1.0"


def _guarded_salt(deployer: str, chain_id: int, salt: bytes) -> bytes:
    sender = bytes.fromhex(deployer[2:])
    guard_flag = salt[20]
    salt_sender = salt[:20]

    if salt_sender == sender and guard_flag == 0x01:
        sender_bytes32 = sender.rjust(32, b"\x00")
        chain_bytes32 = to_bytes(chain_id).rjust(32, b"\x00")
        return keccak(sender_bytes32 + chain_bytes32 + salt)
    if salt_sender == sender and guard_flag == 0x00:
        sender_bytes32 = sender.rjust(32, b"\x00")
        return keccak(sender_bytes32 + salt)
    if salt_sender == b"\x00" * 20 and guard_flag == 0x01:
        chain_bytes32 = to_bytes(chain_id).rjust(32, b"\x00")
        return keccak(chain_bytes32 + salt)
    if salt_sender == sender or salt_sender == b"\x00" * 20:
        raise ValueError("Invalid salt guard byte")
    return keccak(salt)


def main() -> None:
    api_key = os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        raise ValueError("ETHERSCAN_API_KEY is required")

    encrypted_key = os.environ.get("ENCRYPTED_PK")
    if not encrypted_key:
        raise ValueError("ENCRYPTED_PK is required")

    private_key = decrypt_private_key(encrypted_key, getpass())
    deployer = Account.from_key(private_key)
    print(f"Deployer: {deployer.address}")
    deploycode = boa.load_partial(CONTRACT_PATH).compiler_data.bytecode

    boa.set_network_env(RPC_URL)
    boa.env.add_account(deployer)
    boa.env.eoa = deployer.address
    chain_id = boa.env.evm.patch.chain_id
    print(
        f"Chain ID: {chain_id}, Deployer: {deployer.address}, Balance: {boa.env.get_balance(deployer.address) / 1e18}"
    )

    etherscan_url = "https://api.etherscan.io/v2/api"
    boa.set_etherscan(etherscan_url, api_key, chain_id=chain_id)
    createx = boa.from_etherscan(
        CREATE_X_ADDRESS,
        uri=etherscan_url,
        api_key=api_key,
        chain_id=chain_id,
    )
    if not boa.env.get_code(CREATE_X_ADDRESS):
        raise ValueError("CreateX not deployed")

    seed_hash = keccak(text=SALT_SEED_TEXT)
    deployer_bytes = bytes.fromhex(deployer.address[2:])
    salt = deployer_bytes + b"\x00" + seed_hash[:11]
    guarded = _guarded_salt(deployer.address, chain_id, salt)
    address = createx.computeCreate3Address(guarded, CREATE_X_ADDRESS)

    checksum = to_checksum_address(address)
    print(f"Salt: 0x{salt.hex()}")
    print(f"Target: {checksum}")
    if boa.env.get_code(address):
        print(f"{CONTRACT_NAME} already at {checksum}")
    else:
        deployed = createx.deployCreate3(salt, deploycode, sender=deployer.address)

        if deployed != address:
            raise RuntimeError(f"Address mismatch: {deployed} != {checksum}")
        if not boa.env.get_code(address):
            raise RuntimeError("No code at target")

    contract = boa.load_partial(CONTRACT_PATH).at(address)
    contract.ctor_calldata = b""
    verifier = Etherscan(etherscan_url+f"?chainid={chain_id}", api_key)
    boa.verify(contract, verifier=verifier)

    print(f"Deployed {CONTRACT_NAME} at {checksum}")


if __name__ == "__main__":
    main()
