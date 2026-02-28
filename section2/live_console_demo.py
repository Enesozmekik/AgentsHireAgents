from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from eth_account import Account
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_wallet_manager import AgentWalletManager
from mock_worker_logic import MockWorkerLogic, format_delivery_uri
from monad_bridge import MonadBridge, TxResult


console = Console()


@dataclass(frozen=True)
class DemoConfig:
    deployment_file: str
    budget_eth: float
    timeout_sec: int
    prompt: str
    master_name: str
    worker_name: str
    master_expertise: str
    worker_expertise: str
    explorer_tx_base: str


def parse_args() -> DemoConfig:
    parser = argparse.ArgumentParser(description="AME Section 2.4 Live Console demo")
    parser.add_argument("--deployment", default="deployments/monadTestnet.json")
    parser.add_argument("--budget-eth", type=float, default=0.01)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--prompt", default="Summarize agent economy demand signals for this week.")
    parser.add_argument("--master-name", default="Master Agent")
    parser.add_argument("--worker-name", default="Worker Agent")
    parser.add_argument("--master-expertise", default="orchestration")
    parser.add_argument("--worker-expertise", default="execution")
    args = parser.parse_args()

    load_dotenv()
    explorer_tx_base = os.getenv("MONAD_EXPLORER_TX_BASE", "").strip()
    return DemoConfig(
        deployment_file=args.deployment,
        budget_eth=args.budget_eth,
        timeout_sec=args.timeout_sec,
        prompt=args.prompt,
        master_name=args.master_name,
        worker_name=args.worker_name,
        master_expertise=args.master_expertise,
        worker_expertise=args.worker_expertise,
        explorer_tx_base=explorer_tx_base,
    )


def tx_display(tx_hash: str, explorer_tx_base: str) -> str:
    if explorer_tx_base:
        base = explorer_tx_base.rstrip("/")
        return f"{tx_hash} ({base}/{tx_hash})"
    return tx_hash


def run_tx(label: str, fn) -> TxResult:
    with console.status(f"[bold yellow]⌛ Blockchain'e yaziliyor...[/bold yellow] {label}", spinner="dots"):
        result = fn()
    return result


def ensure_registered(
    bridge: MonadBridge,
    account,
    name: str,
    expertise: str,
    explorer_tx_base: str,
) -> None:
    already = bool(bridge.read("isRegistered", account.address))
    if already:
        console.print(f"[green]OK[/green] {name} already registered: {account.address}")
        return

    tx = run_tx(
        f"{name} registerAgent",
        lambda: bridge.send_contract_tx(account, "registerAgent", name, expertise),
    )
    console.print(
        f"[cyan]TX[/cyan] registerAgent/{name}: {tx_display(tx.tx_hash, explorer_tx_base)} "
        f"[dim](status={tx.status}, block={tx.block_number})[/dim]"
    )


def main() -> None:
    cfg = parse_args()

    manager = AgentWalletManager.from_env()
    manager.assert_rpc_connection()
    bridge = MonadBridge.from_deployment_file(manager.w3, cfg.deployment_file)

    master = Account.from_key(manager.master.private_key)
    worker = Account.from_key(manager.worker.private_key)

    summary = manager.summary()
    table = Table(title="AME Live Console")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("RPC Connected", str(summary["rpc_connected"]))
    table.add_row("Chain ID", str(summary["chain_id"]))
    table.add_row("Contract", str(bridge.contract.address))
    table.add_row("Master", str(master.address))
    table.add_row("Worker", str(worker.address))
    console.print(table)

    ensure_registered(
        bridge=bridge,
        account=master,
        name=cfg.master_name,
        expertise=cfg.master_expertise,
        explorer_tx_base=cfg.explorer_tx_base,
    )
    ensure_registered(
        bridge=bridge,
        account=worker,
        name=cfg.worker_name,
        expertise=cfg.worker_expertise,
        explorer_tx_base=cfg.explorer_tx_base,
    )

    budget_wei = int(manager.w3.to_wei(cfg.budget_eth, "ether"))
    next_job_id = int(bridge.read("nextJobId"))
    tx_create = run_tx(
        "createJob",
        lambda: bridge.send_contract_tx(
            master,
            "createJob",
            worker.address,
            cfg.timeout_sec,
            value_wei=budget_wei,
        ),
    )
    console.print(f"[bold]Master Agent:[/bold] Butce kilitlendi. jobId={next_job_id}")
    console.print(f"[cyan]TX[/cyan] createJob: {tx_display(tx_create.tx_hash, cfg.explorer_tx_base)}")

    tx_accept = run_tx("acceptJob", lambda: bridge.send_contract_tx(worker, "acceptJob", next_job_id))
    console.print("[bold]Worker Agent:[/bold] Isi aldim.")
    console.print(f"[cyan]TX[/cyan] acceptJob: {tx_display(tx_accept.tx_hash, cfg.explorer_tx_base)}")

    mock_worker = MockWorkerLogic()
    with console.status("[bold yellow]Worker calisiyor...[/bold yellow]", spinner="bouncingBar"):
        result = mock_worker.run(cfg.prompt)
    delivery_uri = format_delivery_uri(result.output_json)
    console.print("[bold]Worker Agent:[/bold] Is tamamlandi.")
    console.print(Panel.fit(result.summary, title="MockWorkerLogic"))

    tx_submit = run_tx(
        "submitWork",
        lambda: bridge.send_contract_tx(worker, "submitWork", next_job_id, delivery_uri),
    )
    console.print(f"[cyan]TX[/cyan] submitWork: {tx_display(tx_submit.tx_hash, cfg.explorer_tx_base)}")

    tx_approve = run_tx(
        "approveWork",
        lambda: bridge.send_contract_tx(master, "approveWork", next_job_id),
    )
    console.print("[bold green]Chain:[/bold green] Odeme yapildi.")
    console.print(f"[cyan]TX[/cyan] approveWork: {tx_display(tx_approve.tx_hash, cfg.explorer_tx_base)}")

    job = bridge.read("getJob", next_job_id)
    locked = bridge.read("lockedFunds")
    final = Table(title="Final State")
    final.add_column("Metric")
    final.add_column("Value")
    final.add_row("Job Status", str(job[7]))
    final.add_row("Delivery URI", str(job[8])[:120] + ("..." if len(str(job[8])) > 120 else ""))
    final.add_row("Locked Funds", str(locked))
    console.print(final)


if __name__ == "__main__":
    main()
