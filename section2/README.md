# Section 2 - Integration Scaffolds

This folder includes starters for:

- `agent_wallet_manager.py`
- `monad_bridge.py`
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

Expected output includes:

- RPC connection state
- chain id
- master/worker wallet addresses

## Step 2.2 - MonadBridge quick check

Prerequisite:

- Deploy contract first (creates `deployments/monadTestnet.json`)

Run:

- `python section2/bridge_demo.py`

What it does:

- loads deployment ABI/address
- initializes `MonadBridge`
- prints contract address and `lockedFunds`
- shows example write calls (`build -> sign -> send -> wait`) in comments

## Step 2.3 - MockWorkerLogic quick check

Run:

- `python section2/mock_worker_logic.py`

What it does:

- waits ~2-3 seconds to simulate work
- produces structured JSON output
- prints a demo delivery URI string you can pass to `submitWork`

## Step 2.4 - LiveConsole demo

Run:

- `python section2/live_console_demo.py --deployment deployments/monadTestnet.json`

Optional flags:

- `--budget-eth 0.01`
- `--timeout-sec 120`
- `--prompt "your task prompt"`

Optional env:

- `MONAD_EXPLORER_TX_BASE` (for tx link print)

What it does:

- master/worker registration check
- create job with escrow lock
- worker accept
- mock worker generate delivery
- submit work
- approve work and settle payment
- prints TX hash for every blockchain write
