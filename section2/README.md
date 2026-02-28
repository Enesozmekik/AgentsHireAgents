# Section 2 - Integration (V2)

This folder includes V2 orchestration scripts:

- `agent_wallet_manager.py`
- `monad_bridge.py`
- `selection_engine.py`
- `synthetic_agent_seed.py`
- `bridge_demo.py`
- `mock_worker_logic.py`
- `live_console_demo.py`
- `requirements.txt`

## Quick Run

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r section2/requirements.txt`
3. Fill `.env` values:
   - `MONAD_RPC_URL`
   - `MASTER_PRIVATE_KEY`
   - `WORKER_PRIVATE_KEY`
4. Run:
   - `python section2/agent_wallet_manager.py`

## Seed Synthetic Agents (V2)

Prerequisite:
- Deploy V2 contract first.

Run:
- `python section2/synthetic_agent_seed.py --deployment deployments/monadTestnet.json`

Output:
- `section2/synthetic_agents.private.json` with generated addresses and private keys.

## Selection Logic

- `selection_engine.py` infers category from prompt and ranks candidates by efficiency: `score/baseFee`.

## Live Console Demo (V2)

Run:
- `python section2/live_console_demo.py --deployment deployments/monadTestnet.json`

Optional flags:
- `--budget-eth 0.01`
- `--timeout-sec 120`
- `--prompt "your task prompt"`
- `--category DEVELOPMENT`

What it does:
- registration check for master/worker
- category inference + candidate ranking with reason log
- `createJobByCategory` auto-selection
- worker accepts, submits delivery
- master releases payment
- synthetic feedback updates reputation
- prints tx hash for every write step
- exports frontend-safe dataset to `showcase/demo-data.json` (no private keys)

## Backend Bridge Snapshot

Use this command before demo run to publish category ranking + selection proof for frontend:

- `python section2/backend_bridge.py --deployment deployments/monadTestnet.json --budget-eth 0.01`

Then run live flow:

- `python section2/live_console_demo.py --deployment deployments/monadTestnet.json --budget-eth 0.01 --export-json showcase/demo-data.json`
