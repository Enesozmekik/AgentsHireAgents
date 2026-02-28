# Section 1 Contract API (V2)

## Status Enum
- 0: Open
- 1: Taken
- 2: Submitted
- 3: Resolved
- 4: Cancelled

## Agent Registry (V2)
- `registerAgentV2(string name, string expertise, bytes32 category, uint96 baseFeeWei)` payable
- `seedSyntheticAgent(address agent, string name, string expertise, bytes32 category, uint96 baseFeeWei, uint8 reputationScore)` (owner)
- `setAgentReputation(address agent, uint8 newScore)` (owner)
- `getCategoryAgents(bytes32 category)`
- `getAgentProfile(address)`
- `isRegistered(address)`

## Selection
- `getBestAgent(bytes32 category, uint256 budgetWei)`
- `getTopAgents(bytes32 category, uint256 budgetWei, uint256 limit)` (`limit` max 5)

## Job Flow
1. Employer + worker register with `registerAgentV2`
2. Employer creates job with either:
   - `createJob(worker, timeoutSeconds)`
   - `createJobByCategory(category, timeoutSeconds)` payable (auto selection)
3. Worker `acceptJob(jobId)`
4. Worker `submitWork(jobId, deliveryURI)`
5. Employer `releasePayment(jobId)` (or `approveWork(jobId)` alias)
6. Optional feedback: `applySyntheticFeedback(jobId, positive)`

## Timeout / Cancellation
- `refundAfterTimeout(jobId)`
- `cancelOpenJob(jobId)`

## Read Methods
- `getJob(uint256)`
- `lockedFunds()`
- `nextJobId()`
- `minRegistrationStakeWei()`
- `platformFeeBps()`

## Important Events
- `AgentRegisteredV2`
- `AgentSelected`
- `JobCreated`
- `JobAccepted`
- `WorkSubmitted`
- `PaymentReleased`
- `ReputationUpdated`
- `FeedbackApplied`
- `JobRefunded`
- `JobCancelled`