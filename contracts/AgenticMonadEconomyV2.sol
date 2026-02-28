// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title AgenticMonadEconomyV2
 * @notice Reputation-based autonomous marketplace with categorized agents.
 */
contract AgenticMonadEconomyV2 {
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
    error InvalidCategory();
    error InvalidBaseFee();
    error InsufficientStake();
    error NoEligibleAgent();
    error InvalidReputation();
    error FeedbackAlreadyApplied();

    address public owner;

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    uint8 private _unlocked = 1;

    modifier nonReentrant() {
        if (_unlocked != 1) revert Reentrancy();
        _unlocked = 2;
        _;
        _unlocked = 1;
    }

    uint256 public platformFeeBps;
    uint256 public minRegistrationStakeWei;
    uint256 public constant MAX_FEE_BPS = 1_000;
    uint256 public constant EFFICIENCY_SCALE = 1e18;
    uint8 public constant MAX_REPUTATION = 100;
    uint256 public lockedFunds;

    struct AgentProfile {
        string name;
        string expertise;
        bytes32 category;
        uint96 baseFeeWei;
        uint96 stakeWei;
        uint8 reputationScore;
        uint64 totalJobsCompleted;
        bool isRegistered;
    }

    mapping(address => AgentProfile) private agentProfiles;
    mapping(bytes32 => address[]) private categoryAgents;

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
        bytes32 category;
        bool selectedByAlgorithm;
        uint256 selectionScore;
        bool feedbackApplied;
    }

    mapping(uint256 => Job) private jobs;
    uint256 public nextJobId;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event PlatformFeeUpdated(uint256 previousFeeBps, uint256 newFeeBps);
    event MinStakeUpdated(uint256 previousStake, uint256 newStake);
    event AgentRegisteredV2(
        address indexed agent,
        string name,
        string expertise,
        bytes32 indexed category,
        uint256 baseFeeWei,
        uint256 stakeWei
    );
    event ReputationUpdated(address indexed agent, uint256 oldScore, uint256 newScore, bytes32 reason);
    event AgentSelected(uint256 indexed jobId, bytes32 indexed category, address indexed worker, uint256 efficiency);
    event JobCreated(
        uint256 indexed jobId,
        address indexed employer,
        address indexed worker,
        uint256 budget,
        bytes32 category,
        bool selectedByAlgorithm
    );
    event JobAccepted(uint256 indexed jobId, address indexed worker);
    event WorkSubmitted(uint256 indexed jobId, address indexed worker, string deliveryURI);
    event PaymentReleased(
        uint256 indexed jobId,
        address indexed employer,
        address indexed worker,
        uint256 workerPayout,
        uint256 fee
    );
    event FeedbackApplied(uint256 indexed jobId, address indexed worker, bool positive, uint256 newReputation);
    event JobRefunded(uint256 indexed jobId, address indexed employer, uint256 amount);
    event JobCancelled(uint256 indexed jobId, address indexed employer, uint256 amount);

    modifier onlyRegistered() {
        if (!agentProfiles[msg.sender].isRegistered) revert NotRegistered();
        _;
    }

    constructor(uint256 _platformFeeBps, uint256 _minRegistrationStakeWei) {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
        _setPlatformFee(_platformFeeBps);
        minRegistrationStakeWei = _minRegistrationStakeWei;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        address previous = owner;
        owner = newOwner;
        emit OwnershipTransferred(previous, newOwner);
    }

    function setPlatformFeeBps(uint256 newFeeBps) external onlyOwner {
        _setPlatformFee(newFeeBps);
    }

    function setMinRegistrationStakeWei(uint256 newStake) external onlyOwner {
        uint256 previous = minRegistrationStakeWei;
        minRegistrationStakeWei = newStake;
        emit MinStakeUpdated(previous, newStake);
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

    function registerAgentV2(string calldata name, string calldata expertise, bytes32 category, uint96 baseFeeWei)
        external
        payable
    {
        if (category == bytes32(0)) revert InvalidCategory();
        if (baseFeeWei == 0) revert InvalidBaseFee();
        if (msg.value < minRegistrationStakeWei) revert InsufficientStake();

        AgentProfile storage profile = agentProfiles[msg.sender];
        if (profile.isRegistered) revert AlreadyRegistered();

        profile.name = name;
        profile.expertise = expertise;
        profile.category = category;
        profile.baseFeeWei = baseFeeWei;
        profile.stakeWei = uint96(msg.value);
        profile.reputationScore = 50;
        profile.totalJobsCompleted = 0;
        profile.isRegistered = true;

        categoryAgents[category].push(msg.sender);

        emit AgentRegisteredV2(msg.sender, name, expertise, category, baseFeeWei, msg.value);
    }

    function seedSyntheticAgent(
        address agent,
        string calldata name,
        string calldata expertise,
        bytes32 category,
        uint96 baseFeeWei,
        uint8 reputationScore
    ) external onlyOwner {
        if (agent == address(0)) revert ZeroAddress();
        if (category == bytes32(0)) revert InvalidCategory();
        if (baseFeeWei == 0) revert InvalidBaseFee();
        if (reputationScore > MAX_REPUTATION) revert InvalidReputation();
        if (agentProfiles[agent].isRegistered) revert AlreadyRegistered();

        agentProfiles[agent] = AgentProfile({
            name: name,
            expertise: expertise,
            category: category,
            baseFeeWei: baseFeeWei,
            stakeWei: 0,
            reputationScore: reputationScore,
            totalJobsCompleted: 0,
            isRegistered: true
        });
        categoryAgents[category].push(agent);
        emit AgentRegisteredV2(agent, name, expertise, category, baseFeeWei, 0);
    }

    function setAgentReputation(address agent, uint8 newScore) external onlyOwner {
        if (!agentProfiles[agent].isRegistered) revert NotRegistered();
        if (newScore > MAX_REPUTATION) revert InvalidReputation();
        uint8 old = agentProfiles[agent].reputationScore;
        agentProfiles[agent].reputationScore = newScore;
        emit ReputationUpdated(agent, old, newScore, "OWNER_SEED");
    }

    function isRegistered(address agent) external view returns (bool) {
        return agentProfiles[agent].isRegistered;
    }

    function getCategoryAgents(bytes32 category) external view returns (address[] memory) {
        return categoryAgents[category];
    }

    function getAgentProfile(address agent)
        external
        view
        returns (
            string memory name,
            string memory expertise,
            bytes32 category,
            uint256 baseFeeWei,
            uint256 stakeWei,
            uint256 reputationScore,
            uint256 totalJobsCompleted,
            bool registered
        )
    {
        AgentProfile storage p = agentProfiles[agent];
        return (
            p.name,
            p.expertise,
            p.category,
            p.baseFeeWei,
            p.stakeWei,
            p.reputationScore,
            p.totalJobsCompleted,
            p.isRegistered
        );
    }

    function getBestAgent(bytes32 category, uint256 budgetWei)
        public
        view
        returns (address bestAgent, uint256 bestEfficiency, uint256 bestBaseFeeWei, uint256 bestReputation)
    {
        address[] storage agents = categoryAgents[category];
        uint256 length = agents.length;

        for (uint256 i = 0; i < length; i++) {
            address candidate = agents[i];
            AgentProfile storage p = agentProfiles[candidate];
            if (!p.isRegistered || p.baseFeeWei > budgetWei) continue;

            uint256 efficiency = _efficiency(p.reputationScore, p.baseFeeWei);
            if (efficiency > bestEfficiency) {
                bestEfficiency = efficiency;
                bestAgent = candidate;
                bestBaseFeeWei = p.baseFeeWei;
                bestReputation = p.reputationScore;
            }
        }

        if (bestAgent == address(0)) revert NoEligibleAgent();
    }

    function getTopAgents(bytes32 category, uint256 budgetWei, uint256 limit)
        external
        view
        returns (address[] memory agentsOut, uint256[] memory efficiencies)
    {
        if (limit == 0 || limit > 5) limit = 5;
        address[] storage agents = categoryAgents[category];

        address[] memory topAgents = new address[](limit);
        uint256[] memory topScores = new uint256[](limit);

        for (uint256 i = 0; i < agents.length; i++) {
            address candidate = agents[i];
            AgentProfile storage p = agentProfiles[candidate];
            if (!p.isRegistered || p.baseFeeWei > budgetWei) continue;

            uint256 score = _efficiency(p.reputationScore, p.baseFeeWei);
            for (uint256 j = 0; j < limit; j++) {
                if (score > topScores[j]) {
                    for (uint256 k = limit - 1; k > j; k--) {
                        topScores[k] = topScores[k - 1];
                        topAgents[k] = topAgents[k - 1];
                    }
                    topScores[j] = score;
                    topAgents[j] = candidate;
                    break;
                }
            }
        }

        uint256 count = 0;
        for (uint256 i = 0; i < limit; i++) {
            if (topAgents[i] != address(0)) count++;
        }

        agentsOut = new address[](count);
        efficiencies = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            agentsOut[i] = topAgents[i];
            efficiencies[i] = topScores[i];
        }
    }

    function createJob(address worker, uint64 timeoutSeconds) external payable onlyRegistered returns (uint256 jobId) {
        if (worker == address(0)) revert ZeroAddress();
        if (!agentProfiles[worker].isRegistered) revert NotRegistered();
        if (msg.value == 0) revert InvalidBudget();
        if (timeoutSeconds == 0) revert InvalidTimeout();

        jobId = _createJob(msg.sender, worker, msg.value, timeoutSeconds, agentProfiles[worker].category, false, 0);
    }

    function createJobByCategory(bytes32 category, uint64 timeoutSeconds) external payable onlyRegistered returns (uint256 jobId) {
        if (category == bytes32(0)) revert InvalidCategory();
        if (msg.value == 0) revert InvalidBudget();
        if (timeoutSeconds == 0) revert InvalidTimeout();

        (address selected, uint256 score,,) = getBestAgent(category, msg.value);
        jobId = _createJob(msg.sender, selected, msg.value, timeoutSeconds, category, true, score);
        emit AgentSelected(jobId, category, selected, score);
    }

    function _createJob(
        address employer,
        address worker,
        uint256 budget,
        uint64 timeoutSeconds,
        bytes32 category,
        bool selectedByAlgorithm,
        uint256 selectionScore
    ) internal returns (uint256 jobId) {
        jobId = nextJobId;
        unchecked {
            nextJobId = jobId + 1;
        }

        jobs[jobId] = Job({
            employer: employer,
            worker: worker,
            budget: budget,
            createdAt: uint64(block.timestamp),
            acceptedAt: 0,
            timeoutSeconds: timeoutSeconds,
            timeoutAt: 0,
            status: JobStatus.Open,
            deliveryURI: "",
            category: category,
            selectedByAlgorithm: selectedByAlgorithm,
            selectionScore: selectionScore,
            feedbackApplied: false
        });

        lockedFunds += budget;
        emit JobCreated(jobId, employer, worker, budget, category, selectedByAlgorithm);
    }

    function acceptJob(uint256 jobId) external onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Open);
        if (msg.sender != job.worker) revert NotWorker();

        job.status = JobStatus.Taken;
        job.acceptedAt = uint64(block.timestamp);

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

    function approveWork(uint256 jobId) external {
        _releasePayment(jobId);
    }

    function releasePayment(uint256 jobId) external {
        _releasePayment(jobId);
    }

    function _releasePayment(uint256 jobId) internal nonReentrant onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Submitted);
        if (msg.sender != job.employer) revert NotEmployer();

        job.status = JobStatus.Resolved;
        lockedFunds -= job.budget;

        uint256 fee = (job.budget * platformFeeBps) / 10_000;
        uint256 workerPayout = job.budget - fee;

        unchecked {
            agentProfiles[job.worker].totalJobsCompleted += 1;
        }
        _changeReputation(job.worker, 1, true, "JOB_SUCCESS");

        (bool ok, ) = payable(job.worker).call{value: workerPayout}("");
        if (!ok) revert TransferFailed();

        emit PaymentReleased(jobId, msg.sender, job.worker, workerPayout, fee);
    }

    function applySyntheticFeedback(uint256 jobId, bool positive) external onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Resolved);
        if (msg.sender != job.employer) revert NotEmployer();
        if (job.feedbackApplied) revert FeedbackAlreadyApplied();

        job.feedbackApplied = true;
        uint256 newScore = _changeReputation(
            job.worker, 1, positive, positive ? bytes32("FEEDBACK_POS") : bytes32("FEEDBACK_NEG")
        );
        emit FeedbackApplied(jobId, job.worker, positive, newScore);
    }

    function refundAfterTimeout(uint256 jobId) external nonReentrant onlyRegistered {
        Job storage job = jobs[jobId];
        _requireState(job.status, JobStatus.Taken);
        if (msg.sender != job.employer) revert NotEmployer();
        if (block.timestamp <= uint256(job.timeoutAt)) revert TimeoutNotReached();

        job.status = JobStatus.Cancelled;
        lockedFunds -= job.budget;

        _changeReputation(job.worker, 1, false, "TIMEOUT");

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
            string memory deliveryURI,
            bytes32 category,
            bool selectedByAlgorithm,
            uint256 selectionScore,
            bool feedbackApplied
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
            j.deliveryURI,
            j.category,
            j.selectedByAlgorithm,
            j.selectionScore,
            j.feedbackApplied
        );
    }

    function _changeReputation(address agent, uint8 delta, bool increase, bytes32 reason) internal returns (uint8) {
        AgentProfile storage profile = agentProfiles[agent];
        uint8 old = profile.reputationScore;
        uint8 updated;

        if (increase) {
            uint16 next = uint16(old) + delta;
            updated = next > MAX_REPUTATION ? MAX_REPUTATION : uint8(next);
        } else {
            updated = old > delta ? old - delta : 0;
        }

        profile.reputationScore = updated;
        emit ReputationUpdated(agent, old, updated, reason);
        return updated;
    }

    function _efficiency(uint8 score, uint96 baseFeeWei) internal pure returns (uint256) {
        if (baseFeeWei == 0) return 0;
        return (uint256(score) * EFFICIENCY_SCALE) / uint256(baseFeeWei);
    }

    function _requireState(JobStatus current, JobStatus expected) internal pure {
        if (current != expected) revert InvalidState(current, expected);
    }

    receive() external payable {}
}
