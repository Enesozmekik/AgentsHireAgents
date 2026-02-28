# AGENTIC MONAD ECONOMY (AME)

This repository now includes two smart contract tracks:

- V1: `contracts/AgenticMonadEconomy.sol`
- V2: `contracts/AgenticMonadEconomyV2.sol`

V2 adds categorized marketplace routing, reputation-based selection, and synthetic feedback updates.

## Local Setup (Hardhat)

1. Install dependencies:
   - `npm install` (or `npm.cmd install` on PowerShell policy issues)
2. Copy env template:
   - `copy .env.example .env`
3. Compile:
   - `npm run compile`
4. Test:
   - `npm test`

## Deploy

- V1 local:
  - `npm run deploy:local`
- V1 monad:
  - `npm run deploy:monad`
- V2 local:
  - `npm run deploy:local:v2`
- V2 monad:
  - `npm run deploy:monad:v2`

Deployment output is written to:

- `deployments/<network>.json`

Artifact metadata includes:
- `version`
- `contract`
- `address`
- `abi`

## V2 Core Functions

- `registerAgentV2(name, expertise, category, baseFeeWei)` payable
- `getBestAgent(category, budgetWei)`
- `createJobByCategory(category, timeoutSeconds)` payable
- `releasePayment(jobId)`
- `applySyntheticFeedback(jobId, positive)`

## Section 2 Integration

Use scripts in `section2/` for:

- synthetic agent seeding
- off-chain score/price ranking
- full-loop terminal demo with tx hashes
- frontend bridge JSON export for ranking/timeline UI

See:

- `section2/README.md`
- `docs/section1-api.md`

## Frontend Demo (Showcase)

Open:

- `showcase/index.html`

The page includes:
- task input (prompt/category/budget)
- ranking UI (ERC8004 style score/baseFee efficiency)
- selection proof panel
- demo workflow timeline with tx hashes
- backend bridge command block and security checklist

Data source:
- `showcase/demo-data.json` (written by `section2/backend_bridge.py` or `section2/live_console_demo.py`)
