// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title AgenticMonadEconomy
 * @notice Section 1 backend for AME:
 * - Agent registry
 * - Job escrow with locked funds accounting
 * - Job lifecycle state machine
 * - Final settlement and timeout refunds
 */
contract AgenticMonadEconomy {
    // -----------------------------
    // Errors
    // -----------------------------
    error NotOwner();
    error NotRegistered();
    error AlreadyRegistered();
    error ZeroAddress();
    error InvalidState(JobStatus current, JobStatus expected);
    error NotEmployer();
    error NotWorker();
    error InvalidBudget();
    error InvalidTimeout();
    error TimeoutNotReached();
    error TransferFailed();
    error Reentrancy();
    error InsufficientFees();
    error FeeTooHigh();

    // -----------------------------
    // Minimal Ownable
    // -----------------------------
    address public owner;

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    // -----------------------------
    // Minimal ReentrancyGuard
    // -----------------------------
    uint8 private _unlocked = 1;

    modifier nonReentrant() {
        if (_unlocked != 1) revert Reentrancy();
        _unlocked = 2;
        _;
        _unlocked = 1;
    }

    // -----------------------------
    // Config
    // -----------------------------
    uint256 public platformFeeBps; // 100 bps = 1%
    uint256 public constant MAX_FEE_BPS = 1_000; // 10% cap
    uint256 public lockedFunds;

    // -----------------------------
    // Agent registry
    // -----------------------------
    struct AgentProfile {
        string name;
        string expertise;
        uint64 reputationScore;
        uint64 totalJobsCompleted;
        bool isRegistered;
    }

    mapping(address => AgentProfile) private agentProfiles;

    // -----------------------------
    // Job state machine
    // -----------------------------
    enum JobStatus {
        Open,
        Taken,
        Submitted,
        Resolved,
        Cancelled
    }

    struct Job {
        address employer;
        address worker;
        uint256 budget;
        uint64 createdAt;
        uint64 acceptedAt;
        uint64 timeoutSeconds;
        uint64 timeoutAt;
        JobStatus status;
        string deliveryURI;
    }

    mapping(uint256 => Job) private jobs;
    uint256 public nextJobId;

    // -----------------------------
    // Events
    // -----------------------------
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event PlatformFeeUpdated(uint256 previousFeeBps, uint256 newFeeBps);
    event AgentRegistered(address indexed agent, string name, string expertise);
    event JobCreated(uint256 indexed jobId, address indexed employer, address indexed worker, uint256 budget);
    event JobAccepted(uint256 indexed jobId, address indexed worker);
    event WorkSubmitted(uint256 indexed jobId, address indexed worker, string deliveryURI);
    event WorkApproved(
        uint256 indexed jobId,
        address indexed employer,
        address indexed worker,
        uint256 workerPayout,
        uint256 fee
    );
    event JobRefunded(uint256 indexed jobId, address indexed employer, uint256 amount);
    event JobCancelled(uint256 indexed jobId, address indexed employer, uint256 amount);

    modifier onlyRegistered() {
        if (!agentProfiles[msg.sender].isRegistered) revert NotRegistered();
        _;
    }

    constructor(uint256 _platformFeeBps) {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
        _setPlatformFee(_platformFeeBps);
    }

    // -----------------------------
    // Owner controls
    // -----------------------------
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        address previous = owner;
        owner = newOwner;
        emit OwnershipTransferred(previous, newOwner);
    }

    function setPlatformFeeBps(uint256 newFeeBps) external onlyOwner {
        _setPlatformFee(newFeeBps);
    }

    function withdrawFees(address payable to, uint256 amount) external onlyOwner nonReentrant {
        if (to == address(0)) revert ZeroAddress();
        uint256 available = address(this).balance - lockedFunds;
        if (amount > available) revert InsufficientFees();
        (bool ok, ) = to.call{value: amount}("");
        if (!ok) revert TransferFailed();
    }

    function _setPlatformFee(uint256 newFeeBps) internal {
        if (newFeeBps > MAX_FEE_BPS) revert FeeTooHigh();
        uint256 old = platformFeeBps;
        platformFeeBps = newFeeBps;
        emit PlatformFeeUpdated(old, newFeeBps);
    }

    // -----------------------------
    // Agent registry API
    // -----------------------------
    function registerAgent(string calldata name, string calldata expertise) external {
        AgentProfile storage profile = agentProfiles[msg.sender];
        if (profile.isRegistered) revert AlreadyRegistered();

        profile.name = name;
        profile.expertise = expertise;
        profile.reputationScore = 0;
        profile.totalJobsCompleted = 0;
        profile.isRegistered = true;

        emit AgentRegistered(msg.sender, name, expertise);
    }

    function isRegistered(address agent) external view returns (bool) {
        return agentProfiles[agent].isRegistered;
    }

    function getAgentProfile(address agent)
        external
        view
        returns (
            string memory name,
            string memory expertise,
            uint256 reputationScore,
            uint256 totalJobsCompleted,
            bool registered
        )
    {
        AgentProfile storage p = agentProfiles[agent];
        return (p.name, p.expertise, p.reputationScore, p.totalJobsCompleted, p.isRegistered);
    }

    // -----------------------------
    // Job lifecycle API
    // -----------------------------
    function createJob(address worker, uint64 timeoutSeconds) external payable onlyRegistered returns (uint256 jobId) {
        if (worker == address(0)) revert ZeroAddress();
        if (!agentProfiles[worker].isRegistered) revert NotRegistered();
        if (msg.value == 0) revert InvalidBudget();
        if (timeoutSeconds == 0) revert InvalidTimeout();

        jobId = nextJobId;
        unchecked {
            nextJobId = jobId + 1;
        }
        jobs[jobId] = Job({
            employer: msg.sender,
            worker: worker,
            budget: msg.value,
            createdAt: uint64(block.timestamp),
            acceptedAt: 0,
            timeoutSeconds: timeoutSeconds,
            timeoutAt: 0,
            status: JobStatus.Open,
            deliveryURI: ""
        });

        lockedFunds += msg.value;
        emit JobCreated(jobId, msg.sender, worker, msg.value);
    }

    function acceptJob(uint256 jobId) external onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Open);
        if (msg.sender != job.worker) revert NotWorker();

        job.status = JobStatus.Taken;
        job.acceptedAt = uint64(block.timestamp);

        // Countdown starts when worker accepts.
        if (job.timeoutAt == 0) job.timeoutAt = uint64(block.timestamp + job.timeoutSeconds);

        emit JobAccepted(jobId, msg.sender);
    }

    function submitWork(uint256 jobId, string calldata deliveryURI) external onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Taken);
        if (msg.sender != job.worker) revert NotWorker();

        job.status = JobStatus.Submitted;
        job.deliveryURI = deliveryURI;

        emit WorkSubmitted(jobId, msg.sender, deliveryURI);
    }

    function approveWork(uint256 jobId) external nonReentrant onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Submitted);
        if (msg.sender != job.employer) revert NotEmployer();

        job.status = JobStatus.Resolved;
        lockedFunds -= job.budget;

        uint256 fee = (job.budget * platformFeeBps) / 10_000;
        uint256 workerPayout = job.budget - fee;

        unchecked {
            agentProfiles[job.worker].totalJobsCompleted += 1;
            agentProfiles[job.worker].reputationScore += 1;
        }

        (bool ok, ) = payable(job.worker).call{value: workerPayout}("");
        if (!ok) revert TransferFailed();

        emit WorkApproved(jobId, msg.sender, job.worker, workerPayout, fee);
    }

    function refundAfterTimeout(uint256 jobId) external nonReentrant onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Taken);
        if (msg.sender != job.employer) revert NotEmployer();
        if (block.timestamp <= uint256(job.timeoutAt)) revert TimeoutNotReached();

        job.status = JobStatus.Cancelled;
        lockedFunds -= job.budget;

        (bool ok, ) = payable(job.employer).call{value: job.budget}("");
        if (!ok) revert TransferFailed();

        emit JobRefunded(jobId, job.employer, job.budget);
    }

    function cancelOpenJob(uint256 jobId) external nonReentrant onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Open);
        if (msg.sender != job.employer) revert NotEmployer();

        job.status = JobStatus.Cancelled;
        lockedFunds -= job.budget;

        (bool ok, ) = payable(job.employer).call{value: job.budget}("");
        if (!ok) revert TransferFailed();

        emit JobCancelled(jobId, job.employer, job.budget);
    }

    // -----------------------------
    // Read API
    // -----------------------------
    function getJob(uint256 jobId)
        external
        view
        returns (
            address employer,
            address worker,
            uint256 budget,
            uint256 createdAt,
            uint256 acceptedAt,
            uint64 timeoutSeconds,
            uint256 timeoutAt,
            JobStatus status,
            string memory deliveryURI
        )
    {
        Job storage j = jobs[jobId];
        return (
            j.employer,
            j.worker,
            j.budget,
            uint256(j.createdAt),
            uint256(j.acceptedAt),
            j.timeoutSeconds,
            uint256(j.timeoutAt),
            j.status,
            j.deliveryURI
        );
    }

    // Optional helper for Section 2 to override per-job timeout when creating.
    function setJobTimeoutAt(uint256 jobId, uint256 timeoutAtTs) external onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Open);
        if (msg.sender != job.employer) revert NotEmployer();
        if (timeoutAtTs <= block.timestamp || timeoutAtTs > type(uint64).max) revert InvalidTimeout();
        job.timeoutAt = uint64(timeoutAtTs);
    }

    // -----------------------------
    // Internal utils
    // -----------------------------
    function _requireState(JobStatus current, JobStatus expected) internal pure {
        if (current != expected) revert InvalidState(current, expected);
    }

    receive() external payable {}
}
