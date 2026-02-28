# Section 1 Contract API

## Status Enum
- 0: Open
- 1: Taken
- 2: Submitted
- 3: Resolved
- 4: Cancelled

## Typical Flow
1. Employer + Worker call `registerAgent(...)`
2. Employer calls `createJob(worker, timeoutSeconds)` with native coin as `msg.value`
3. Worker calls `acceptJob(jobId)`
4. Worker calls `submitWork(jobId, deliveryURI)`
5. Employer calls `approveWork(jobId)` -> worker gets paid

## Timeout Refund Flow
1. Worker accepted job (`Taken`)
2. Timeout passes (`block.timestamp > timeoutAt`)
3. Employer calls `refundAfterTimeout(jobId)`

## Cancel Before Accept
- Employer can call `cancelOpenJob(jobId)` only while job is `Open`.

## Read Methods for Integrator
- `isRegistered(address)`
- `getAgentProfile(address)`
- `getJob(uint256)`
- `lockedFunds()`
- `nextJobId()`

## Important Events to Stream
- `JobCreated(jobId, employer, worker, budget)`
- `JobAccepted(jobId, worker)`
- `WorkSubmitted(jobId, worker, deliveryURI)`
- `WorkApproved(jobId, employer, worker, workerPayout, fee)`
- `JobRefunded(jobId, employer, amount)`
- `JobCancelled(jobId, employer, amount)`
