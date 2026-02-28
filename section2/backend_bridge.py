from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from agent_wallet_manager import AgentWalletManager
from monad_bridge import MonadBridge
from selection_engine import Candidate, infer_category, select_best


def to_bytes32(category: str) -> bytes:
    raw = category.encode("utf-8")
    if len(raw) > 32:
        raise ValueError("Category is too long for bytes32")
    return raw + (b"\x00" * (32 - len(raw)))


def decode_category(category_b32: bytes) -> str:
    return category_b32.decode("utf-8", errors="ignore").rstrip("\x00")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build frontend snapshot JSON from on-chain state")
    parser.add_argument("--deployment", default="deployments/monadTestnet.json")
    parser.add_argument("--prompt", default="Build a backend bridge for post-demo selection run.")
    parser.add_argument("--category", default="")
    parser.add_argument("--budget-eth", type=float, default=0.01)
    parser.add_argument("--output", default="showcase/demo-data.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()
    bridge = MonadBridge.from_deployment_file(manager.w3, args.deployment)

    category_text = (args.category or "").strip().upper() or infer_category(args.prompt)
    category_b32 = to_bytes32(category_text)
    budget_wei = int(manager.w3.to_wei(args.budget_eth, "ether"))

    addresses = bridge.read("getCategoryAgents", category_b32)
    candidates: list[Candidate] = []
    for address in addresses:
        p = bridge.read("getAgentProfile", address)
        if not p[7]:
            continue
        candidates.append(
            Candidate(
                address=address,
                category=decode_category(p[2]),
                base_fee_wei=int(p[3]),
                reputation_score=int(p[5]),
            )
        )

    selection = select_best(candidates, category_text, budget_wei)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "network": {
            "chainId": int(manager.w3.eth.chain_id),
            "contractAddress": bridge.contract.address,
        },
        "task": {
            "prompt": args.prompt,
            "category": category_text,
            "budgetWei": budget_wei,
            "budgetEth": args.budget_eth,
            "jobId": None,
        },
        "ranking": [
            {
                "address": c.address,
                "category": c.category,
                "baseFeeWei": c.base_fee_wei,
                "reputation": c.reputation_score,
                "efficiency": c.efficiency,
            }
            for c in selection.candidates
        ],
        "selectionProof": {
            "selectedAgent": selection.best.address,
            "selectedBaseFeeWei": selection.best.base_fee_wei,
            "selectedReputation": selection.best.reputation_score,
            "selectedEfficiency": selection.best.efficiency,
            "reason": selection.reason,
        },
        "workflow": {
            "steps": [
                {"key": "createJobByCategory", "label": "Budget escrow lock (pending demo run)", "status": "pending", "txHash": ""},
                {"key": "acceptJob", "label": "Worker accept (pending demo run)", "status": "pending", "txHash": ""},
                {"key": "submitWork", "label": "Submission (pending demo run)", "status": "pending", "txHash": ""},
                {"key": "releasePayment", "label": "Payment release (pending demo run)", "status": "pending", "txHash": ""},
                {"key": "applySyntheticFeedback", "label": "Feedback update (pending demo run)", "status": "pending", "txHash": ""},
            ]
        },
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Frontend snapshot written: {out}")


if __name__ == "__main__":
    main()
