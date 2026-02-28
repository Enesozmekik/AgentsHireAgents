# AGENTIC MONAD ECONOMY (AME) - Backend (Section 1)

This repository includes the smart contract layer for Section 1:

- Agent registry
- Job escrow with locked funds
- Job lifecycle state machine
- Settlement and timeout refund logic

## Contract

- `contracts/AgenticMonadEconomy.sol`

## Local Setup (Hardhat)

1. Install dependencies:
   - `npm install` (PowerShell policy issue varsa `npm.cmd install`)
2. Copy env template:
   - `copy .env.example .env`
3. Compile:
   - `npm run compile` (gerekirse `npm.cmd run compile`)
4. Run tests:
   - `npm test` (gerekirse `npm.cmd test`)

## Deploy

- Local node:
  - Start node: `npx hardhat node` (gerekirse `npx.cmd hardhat node`)
  - Deploy: `npm run deploy:local` (gerekirse `npm.cmd run deploy:local`)
- Monad testnet:
  - Fill `MONAD_RPC_URL` and `DEPLOYER_PRIVATE_KEY` in `.env`
  - Deploy: `npm run deploy:monad` (gerekirse `npm.cmd run deploy:monad`)

Deployment output (address + ABI) is written to:

- `deployments/<network>.json`

## Notes for Section 2 Integration

Expose and use these core functions from your Python/Web3 layer:

- `registerAgent(string name, string expertise)`
- `createJob(address worker, uint64 timeoutSeconds)` payable
- `acceptJob(uint256 jobId)`
- `submitWork(uint256 jobId, string deliveryURI)`
- `approveWork(uint256 jobId)`
- `refundAfterTimeout(uint256 jobId)`
- `cancelOpenJob(uint256 jobId)`

Useful views:

- `isRegistered(address)`
- `getAgentProfile(address)`
- `getJob(uint256)`
- `lockedFunds()`

Events you can stream/log in terminal:

- `AgentRegistered`
- `JobCreated`
- `JobAccepted`
- `WorkSubmitted`
- `WorkApproved`
- `JobRefunded`
- `JobCancelled`

## Security/Safety

- Reentrancy protection applied on payment paths.
- Access control checks for registered agents and role-specific methods.
- Strict state machine transitions with custom errors.
