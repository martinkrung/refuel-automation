# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "titanoboa==0.2.8",
# ]
# ///
"""
Auto-refuel script for DonationStreamer contracts.
Executes due streams across multiple chains.
"""

import argparse
import sys

import boa


DONATION_STREAMER = "0x2b786BB995978CC2242C567Ae62fd617b0eBC828"

ALCHEMY_RPC_BASE = "https://{network}-mainnet.g.alchemy.com/v2/{api_key}"

CHAINS = {
    "gnosis": {
        "chain_id": 100,
        "alchemy_network": "gnosis",
        "explorer": "https://gnosisscan.io",
    },
    "ethereum": {
        "chain_id": 1,
        "alchemy_network": "eth",
        "explorer": "https://etherscan.io",
    },
    "base": {
        "chain_id": 8453,
        "alchemy_network": "base",
        "explorer": "https://basescan.org",
    },
}


def get_streamer_contract():
    """Load DonationStreamer contract interface."""
    return boa.load_partial("contracts/DonationStreamer.vy").at(DONATION_STREAMER)


def execute_refuel(chain: str, rpc_url: str, private_key: str, dry_run: bool) -> bool:
    """Execute refuel for a single chain."""
    config = CHAINS[chain]
    print(f"\n{'='*60}")
    print(f"Chain: {chain.upper()} (ID: {config['chain_id']})")
    print(f"{'='*60}")

    boa.set_network_env(rpc_url)

    if private_key:
        from eth_account import Account

        account = Account.from_key(private_key)
        boa.env.add_account(account)
        boa.env.eoa = account.address
        print(f"Executor: {account.address}")
        balance = boa.env.get_balance(account.address)
        print(f"Balance: {balance / 1e18:.6f} native")
    else:
        # Set a dummy EOA for read-only operations
        boa.env.eoa = "0x0000000000000000000000000000000000000000"

    streamer = get_streamer_contract()
    due_ids, rewards = streamer.streams_and_rewards_due()

    if not due_ids:
        print("No streams due for execution.")
        return True

    total_reward = sum(rewards)
    print(f"Due streams: {len(due_ids)}")
    print(f"Stream IDs: {list(due_ids)}")
    print(f"Total reward: {total_reward / 1e18:.6f} native")

    if dry_run:
        print("[DRY RUN] Would execute streams, skipping actual transaction.")
        return True

    if not private_key:
        print("ERROR: Private key required for execution (non-dry-run mode).")
        return False

    print("Executing streams...")

    # Get current base fee and set max_fee as low as possible
    latest_block = boa.env.evm.patch.get_block("latest")
    base_fee = latest_block["baseFeePerGas"]
    max_priority_fee = 1  # minimal priority, we don't care about speed
    max_fee = base_fee + max_priority_fee  # just above base fee

    print(f"Gas Fees: Base={base_fee / 1e9:.6f} Gwei | Max={max_fee / 1e9:.6f} Gwei | Priority={max_priority_fee / 1e9:.6f} Gwei")

    try:
        tx = streamer.execute_many(list(due_ids), max_priority_fee=max_priority_fee, max_fee=max_fee)
        print("Transaction successful!")
        print(f"Explorer: {config['explorer']}/tx/{tx.txhash.hex() if hasattr(tx, 'txhash') else 'pending'}")
        return True
    except Exception as e:
        print(f"ERROR: Transaction failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Auto-refuel for DonationStreamer")
    parser.add_argument(
        "--chains",
        nargs="+",
        choices=list(CHAINS.keys()) + ["all"],
        default=["all"],
        help="Chains to refuel (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (no transactions)",
    )
    parser.add_argument(
        "--alchemy-api-key",
        help="Alchemy API key (or set ALCHEMY_RPC_API_KEY env)",
    )
    parser.add_argument(
        "--private-key",
        help="Private key for signing (or set PRIVATE_KEY env)",
    )
    args = parser.parse_args()

    import os

    private_key = args.private_key or os.environ.get("PRIVATE_KEY")
    alchemy_api_key = args.alchemy_api_key or os.environ.get("ALCHEMY_RPC_API_KEY")

    if not alchemy_api_key:
        print("ERROR: Alchemy API key required (--alchemy-api-key or ALCHEMY_RPC_API_KEY env)")
        sys.exit(1)

    rpc_urls = {
        chain: ALCHEMY_RPC_BASE.format(network=config["alchemy_network"], api_key=alchemy_api_key)
        for chain, config in CHAINS.items()
    }

    chains_to_run = list(CHAINS.keys()) if "all" in args.chains else args.chains

    print("=" * 60)
    print("DonationStreamer Auto-Refuel")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Chains: {', '.join(chains_to_run)}")
    print(f"DonationStreamer: {DONATION_STREAMER}")

    import time

    results = {}
    for i, chain in enumerate(chains_to_run):
        if i > 0:
            time.sleep(1)

        rpc_url = rpc_urls.get(chain)
        if not rpc_url:
            print(f"\nWARNING: Skipping {chain} - no RPC URL configured")
            results[chain] = None
            continue

        try:
            success = execute_refuel(chain, rpc_url, private_key, args.dry_run)
            results[chain] = success
        except Exception as e:
            print(f"\nERROR on {chain}: {e}")
            results[chain] = False

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for chain, result in results.items():
        status = "SKIPPED" if result is None else ("OK" if result else "FAILED")
        print(f"  {chain}: {status}")

    failed = [c for c, r in results.items() if r is False]
    if failed:
        print(f"\nFailed chains: {', '.join(failed)}")
        sys.exit(1)

    print("\nAll configured chains processed successfully.")


if __name__ == "__main__":
    main()
