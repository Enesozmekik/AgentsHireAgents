from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account

from agent_wallet_manager import AgentWalletManager
from monad_bridge import MonadBridge


@dataclass(frozen=True)
class SeedSpec:
    name: str
    category: bytes
    base_fee_wei: int
    reputation: int


CATEGORY_BYTES = {
    "DEVELOPMENT": b"DEVELOPMENT" + b"\x00" * (32 - len("DEVELOPMENT")),
    "RESEARCH": b"RESEARCH" + b"\x00" * (32 - len("RESEARCH")),
    "DATA_MINING": b"DATA_MINING" + b"\x00" * (32 - len("DATA_MINING")),
    "CONTENT_GEN": b"CONTENT_GEN" + b"\x00" * (32 - len("CONTENT_GEN")),
}


def make_specs() -> list[SeedSpec]:
    specs: list[SeedSpec] = []
    tier_values = [
        ("high", 250_000_000_000_000, 92),
        ("mid", 150_000_000_000_000, 75),
        ("low", 80_000_000_000_000, 45),
    ]
    for category_name, category_bytes in CATEGORY_BYTES.items():
        for label, fee, score in tier_values:
            specs.append(
                SeedSpec(
                    name=f"{category_name}_{label}",
                    category=category_bytes,
                    base_fee_wei=fee,
                    reputation=score,
                )
            )
    return specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed synthetic V2 agents")
    parser.add_argument("--deployment", default="deployments/monadTestnet.json")
    parser.add_argument("--output", default="section2/synthetic_agents.private.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()

    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()
    bridge = MonadBridge.from_deployment_file(manager.w3, args.deployment)

    owner_key = (os.getenv("DEPLOYER_PRIVATE_KEY") or manager.master.private_key).strip()
    owner_account = Account.from_key(owner_key)
    specs = make_specs()
    seeded_records = []

    for spec in specs:
        synthetic = Account.create()
        tx = bridge.send_contract_tx(
            owner_account,
            "seedSyntheticAgent",
            synthetic.address,
            spec.name,
            "synthetic",
            spec.category,
            spec.base_fee_wei,
            spec.reputation,
        )

        seeded_records.append(
            {
                "address": synthetic.address,
                "private_key": synthetic.key.hex(),
                "name": spec.name,
                "category_hex": "0x" + spec.category.hex(),
                "base_fee_wei": spec.base_fee_wei,
                "reputation": spec.reputation,
                "tx_hash": tx.tx_hash,
            }
        )
        print(f"Seeded {spec.name}: {synthetic.address} tx={tx.tx_hash}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"agents": seeded_records}, indent=2), encoding="utf-8")
    print(f"Wrote synthetic agent keys to {out_path}")


if __name__ == "__main__":
    main()
