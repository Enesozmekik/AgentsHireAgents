from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_runtime import AgentRuntime
from agent_wallet_manager import AgentWalletManager
from mock_worker_logic import MockWorkerLogic, format_delivery_uri
from monad_bridge import MonadBridge, TxResult
from selection_engine import Candidate, infer_category, select_best


console = Console()


@dataclass(frozen=True)
class DemoConfig:
    deployment_file: str
    budget_eth: float
    timeout_sec: int
    prompt: str
    category: str
    master_name: str
    worker_name: str
    master_expertise: str
    worker_expertise: str
    worker_base_fee_wei: int
    synthetic_agents_file: str
    explorer_tx_base: str
    export_json: str


def parse_args() -> DemoConfig:
    parser = argparse.ArgumentParser(description="AME V2 Live Console demo")
    parser.add_argument("--deployment", default="deployments/monadTestnet.json")
    parser.add_argument("--budget-eth", type=float, default=0.01)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--prompt", default="Analyze market demand for agentic coding services.")
    parser.add_argument("--category", default="")
    parser.add_argument("--master-name", default="Master Agent")
    parser.add_argument("--worker-name", default="Worker Agent")
    parser.add_argument("--master-expertise", default="orchestration")
    parser.add_argument("--worker-expertise", default="execution")
    parser.add_argument("--worker-base-fee-wei", type=int, default=100000000000000)
    parser.add_argument("--synthetic-agents-file", default="section2/synthetic_agents.private.json")
    parser.add_argument("--export-json", default="showcase/demo-data.json")
    args = parser.parse_args()

    load_dotenv()
    explorer_tx_base = os.getenv("MONAD_EXPLORER_TX_BASE", "").strip()
    return DemoConfig(
        deployment_file=args.deployment,
        budget_eth=args.budget_eth,
        timeout_sec=args.timeout_sec,
        prompt=args.prompt,
        category=(args.category or "").strip().upper(),
        master_name=args.master_name,
        worker_name=args.worker_name,
        master_expertise=args.master_expertise,
        worker_expertise=args.worker_expertise,
        worker_base_fee_wei=args.worker_base_fee_wei,
        synthetic_agents_file=args.synthetic_agents_file,
        explorer_tx_base=explorer_tx_base,
        export_json=args.export_json,
    )


def to_bytes32(category: str) -> bytes:
    raw = category.encode("utf-8")
    if len(raw) > 32:
        raise ValueError("category is too long for bytes32")
    return raw + (b"\x00" * (32 - len(raw)))


def tx_display(tx_hash: str, explorer_tx_base: str) -> str:
    if explorer_tx_base:
        base = explorer_tx_base.rstrip("/")
        return f"{tx_hash} ({base}/{tx_hash})"
    return tx_hash


def run_tx(label: str, fn) -> TxResult:
    with console.status(f"[bold yellow]Writing to chain...[/bold yellow] {label}", spinner="dots"):
        result = fn()
    return result


def ensure_registered_v2(
    bridge: MonadBridge,
    account,
    name: str,
    expertise: str,
    category_b32: bytes,
    base_fee_wei: int,
    stake_wei: int,
    explorer_tx_base: str,
) -> None:
    already = bool(bridge.read("isRegistered", account.address))
    if already:
        console.print(f"[green]OK[/green] {name} already registered: {account.address}")
        return

    tx = run_tx(
        f"registerAgentV2/{name}",
        lambda: bridge.send_contract_tx(
            account,
            "registerAgentV2",
            name,
            expertise,
            category_b32,
            base_fee_wei,
            value_wei=stake_wei,
        ),
    )
    console.print(
        f"[cyan]TX[/cyan] registerAgentV2/{name}: {tx_display(tx.tx_hash, explorer_tx_base)} "
        f"[dim](status={tx.status}, block={tx.block_number})[/dim]"
    )


def decode_category(category_b32: bytes) -> str:
    return category_b32.decode("utf-8", errors="ignore").rstrip("\x00")


def wei_to_eth_str(wei_value: int, decimals: int = 6) -> str:
    scale = 10**18
    whole = wei_value // scale
    frac = wei_value % scale
    frac_text = str(frac).rjust(18, "0")[:decimals].rstrip("0")
    return f"{whole}.{frac_text or '0'}"


def write_demo_export(
    cfg: DemoConfig,
    bridge: MonadBridge,
    job_id: int,
    budget_wei: int,
    category_text: str,
    prompt: str,
    selection: "SelectionResult",
    tx_hashes: dict[str, str],
    feedback_positive: bool,
) -> None:
    ranked_agents = [
        {
            "address": candidate.address,
            "category": candidate.category,
            "baseFeeWei": candidate.base_fee_wei,
            "reputation": candidate.reputation_score,
            "efficiency": candidate.efficiency,
        }
        for candidate in selection.candidates
    ]

    selected = selection.best
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "network": {
            "chainId": int(bridge.w3.eth.chain_id),
            "contractAddress": bridge.contract.address,
            "explorerTxBase": cfg.explorer_tx_base,
        },
        "task": {
            "prompt": prompt,
            "category": category_text,
            "budgetWei": budget_wei,
            "budgetEth": wei_to_eth_str(budget_wei),
            "jobId": job_id,
        },
        "ranking": ranked_agents,
        "selectionProof": {
            "selectedAgent": selected.address,
            "selectedBaseFeeWei": selected.base_fee_wei,
            "selectedReputation": selected.reputation_score,
            "selectedEfficiency": selected.efficiency,
            "reason": selection.reason,
        },
        "workflow": {
            "steps": [
                {"key": "createJobByCategory", "label": "Budget escrow locked", "status": "done", "txHash": tx_hashes["createJobByCategory"]},
                {"key": "acceptJob", "label": "Worker accepted the job", "status": "done", "txHash": tx_hashes["acceptJob"]},
                {"key": "submitWork", "label": "Worker submitted delivery proof", "status": "done", "txHash": tx_hashes["submitWork"]},
                {"key": "releasePayment", "label": "Payment released to worker", "status": "done", "txHash": tx_hashes["releasePayment"]},
                {"key": "applySyntheticFeedback", "label": "Reputation feedback applied", "status": "done", "txHash": tx_hashes["applySyntheticFeedback"]},
            ],
            "feedbackPositive": feedback_positive,
        },
    }

    out_path = Path(cfg.export_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"[green]Export[/green] Frontend demo data written: {out_path}")


def main() -> None:
    cfg = parse_args()

    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()
    bridge = MonadBridge.from_deployment_file(manager.w3, cfg.deployment_file)
    runtime = AgentRuntime(manager.w3, cfg.synthetic_agents_file)

    master = Account.from_key(manager.master.private_key)
    worker = Account.from_key(manager.worker.private_key)

    category_text = cfg.category or infer_category(cfg.prompt)
    category_b32 = to_bytes32(category_text)

    stake_wei = int(bridge.read("minRegistrationStakeWei"))

    summary = manager.summary()
    table = Table(title="AME V2 Live Console")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("RPC Connected", str(summary["rpc_connected"]))
    table.add_row("Chain ID", str(summary["chain_id"]))
    table.add_row("Contract", str(bridge.contract.address))
    table.add_row("Master", str(master.address))
    table.add_row("Worker", str(worker.address))
    table.add_row("Category", category_text)
    console.print(table)

    ensure_registered_v2(
        bridge,
        master,
        cfg.master_name,
        cfg.master_expertise,
        category_b32,
        cfg.worker_base_fee_wei,
        stake_wei,
        cfg.explorer_tx_base,
    )
    ensure_registered_v2(
        bridge,
        worker,
        cfg.worker_name,
        cfg.worker_expertise,
        category_b32,
        cfg.worker_base_fee_wei,
        stake_wei,
        cfg.explorer_tx_base,
    )

    budget_wei = int(manager.w3.to_wei(cfg.budget_eth, "ether"))
    addresses = bridge.read("getCategoryAgents", category_b32)

    candidates: list[Candidate] = []
    for address in addresses:
        profile = bridge.read("getAgentProfile", address)
        if not profile[7]:
            continue
        candidates.append(
            Candidate(
                address=address,
                category=decode_category(profile[2]),
                base_fee_wei=int(profile[3]),
                reputation_score=int(profile[5]),
            )
        )

    selection = select_best(candidates, category_text, budget_wei)
    console.print(Panel.fit(selection.reason, title="Selection Reason"))

    next_job_id = int(bridge.read("nextJobId"))
    tx_create = run_tx(
        "createJobByCategory",
        lambda: bridge.send_contract_tx(master, "createJobByCategory", category_b32, cfg.timeout_sec, value_wei=budget_wei),
    )
    console.print(f"[bold]Master Agent:[/bold] Job opened with auto-selection. jobId={next_job_id}")
    console.print(f"[cyan]TX[/cyan] createJobByCategory: {tx_display(tx_create.tx_hash, cfg.explorer_tx_base)}")

    job = bridge.read("getJob", next_job_id)
    selected_worker = job[1]
    selected_worker_account = runtime.get_synthetic_account(selected_worker)
    gas_topup_tx = runtime.ensure_agent_gas(master, selected_worker_account.address)
    if gas_topup_tx:
        console.print(f"[cyan]TX[/cyan] gasTopup: {tx_display(gas_topup_tx, cfg.explorer_tx_base)}")

    tx_accept = run_tx("acceptJob", lambda: bridge.send_contract_tx(selected_worker_account, "acceptJob", next_job_id))
    console.print(f"[bold]Worker Agent:[/bold] Job accepted by {selected_worker_account.address}.")
    console.print(f"[cyan]TX[/cyan] acceptJob: {tx_display(tx_accept.tx_hash, cfg.explorer_tx_base)}")

    mock_worker = MockWorkerLogic()
    with console.status("[bold yellow]Worker running...[/bold yellow]", spinner="bouncingBar"):
        result = mock_worker.run(cfg.prompt)
    delivery_uri = format_delivery_uri(result.output_json)
    console.print("[bold]Worker Agent:[/bold] Work completed.")
    console.print(Panel.fit(result.summary, title="MockWorkerLogic"))

    tx_submit = run_tx(
        "submitWork",
        lambda: bridge.send_contract_tx(selected_worker_account, "submitWork", next_job_id, delivery_uri),
    )
    console.print(f"[cyan]TX[/cyan] submitWork: {tx_display(tx_submit.tx_hash, cfg.explorer_tx_base)}")

    tx_release = run_tx(
        "releasePayment",
        lambda: bridge.send_contract_tx(master, "releasePayment", next_job_id),
    )
    console.print("[bold green]Chain:[/bold green] Payment released.")
    console.print(f"[cyan]TX[/cyan] releasePayment: {tx_display(tx_release.tx_hash, cfg.explorer_tx_base)}")

    feedback_positive = random.choice([True, False])
    tx_feedback = run_tx(
        "applySyntheticFeedback",
        lambda: bridge.send_contract_tx(master, "applySyntheticFeedback", next_job_id, feedback_positive),
    )
    feedback_label = "Great job" if feedback_positive else "Delayed delivery"
    console.print(f"[bold]Feedback:[/bold] {feedback_label}")
    console.print(f"[cyan]TX[/cyan] applySyntheticFeedback: {tx_display(tx_feedback.tx_hash, cfg.explorer_tx_base)}")

    final_job = bridge.read("getJob", next_job_id)
    profile = bridge.read("getAgentProfile", selected_worker_account.address)
    locked = bridge.read("lockedFunds")

    final = Table(title="Final State")
    final.add_column("Metric")
    final.add_column("Value")
    final.add_row("Job Status", str(final_job[7]))
    final.add_row("Feedback Applied", str(final_job[12]))
    final.add_row("Worker", str(selected_worker_account.address))
    final.add_row("Worker Reputation", str(profile[5]))
    final.add_row("Locked Funds", str(locked))
    console.print(final)

    write_demo_export(
        cfg=cfg,
        bridge=bridge,
        job_id=next_job_id,
        budget_wei=budget_wei,
        category_text=category_text,
        prompt=cfg.prompt,
        selection=selection,
        tx_hashes={
            "createJobByCategory": tx_create.tx_hash,
            "acceptJob": tx_accept.tx_hash,
            "submitWork": tx_submit.tx_hash,
            "releasePayment": tx_release.tx_hash,
            "applySyntheticFeedback": tx_feedback.tx_hash,
        },
        feedback_positive=feedback_positive,
    )


if __name__ == "__main__":
    main()
