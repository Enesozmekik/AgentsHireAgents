const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgenticMonadEconomyV2", function () {
  const CATEGORY_DEV = ethers.encodeBytes32String("DEVELOPMENT");
  const CATEGORY_RESEARCH = ethers.encodeBytes32String("RESEARCH");

  async function deployFixture() {
    const [owner, employer, worker1, worker2, worker3] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("AgenticMonadEconomyV2");
    const ame = await Factory.deploy(100, ethers.parseEther("0.01"));
    await ame.waitForDeployment();
    return { ame, owner, employer, worker1, worker2, worker3 };
  }

  it("registers agent with category/base fee/stake", async function () {
    const { ame, worker1 } = await deployFixture();

    await expect(
      ame
        .connect(worker1)
        .registerAgentV2("Dev A", "smart contracts", CATEGORY_DEV, 1000, { value: ethers.parseEther("0.01") })
    )
      .to.emit(ame, "AgentRegisteredV2");

    const profile = await ame.getAgentProfile(worker1.address);
    expect(profile.registered).to.equal(true);
    expect(profile.category).to.equal(CATEGORY_DEV);
    expect(profile.baseFeeWei).to.equal(1000n);
    expect(profile.reputationScore).to.equal(50n);

    await expect(
      ame
        .connect(worker1)
        .registerAgentV2("Dev A", "smart contracts", CATEGORY_DEV, 1000, { value: ethers.parseEther("0.01") })
    ).to.be.reverted;
  });

  it("auto-selects best efficiency agent by category and budget", async function () {
    const { ame, owner, employer, worker1, worker2, worker3 } = await deployFixture();

    const stake = { value: ethers.parseEther("0.01") };
    await ame.connect(employer).registerAgentV2("Master", "orchestration", CATEGORY_RESEARCH, 2000, stake);

    await ame.connect(worker1).registerAgentV2("HighPriceHighScore", "dev", CATEGORY_DEV, 4000, stake);
    await ame.connect(worker2).registerAgentV2("Mid", "dev", CATEGORY_DEV, 2000, stake);
    await ame.connect(worker3).registerAgentV2("Budget", "dev", CATEGORY_DEV, 1000, stake);

    await ame.connect(owner).setAgentReputation(worker1.address, 92);
    await ame.connect(owner).setAgentReputation(worker2.address, 70);
    await ame.connect(owner).setAgentReputation(worker3.address, 45);

    const best = await ame.getBestAgent(CATEGORY_DEV, 2500);
    expect(best.bestAgent).to.equal(worker3.address);

    const budget = ethers.parseEther("1");
    await expect(ame.connect(employer).createJobByCategory(CATEGORY_DEV, 3600, { value: budget }))
      .to.emit(ame, "AgentSelected");

    const job = await ame.getJob(0);
    expect(job.worker).to.equal(worker3.address);
    expect(job.selectedByAlgorithm).to.equal(true);
  });

  it("updates reputation on payment + synthetic feedback", async function () {
    const { ame, owner, employer, worker1 } = await deployFixture();

    const stake = { value: ethers.parseEther("0.01") };
    await ame.connect(employer).registerAgentV2("Master", "orchestration", CATEGORY_RESEARCH, 1000, stake);
    await ame.connect(worker1).registerAgentV2("Worker", "dev", CATEGORY_DEV, 1000, stake);

    await ame.connect(owner).setAgentReputation(worker1.address, 60);

    const budget = ethers.parseEther("0.2");
    await ame.connect(employer).createJob(worker1.address, 600, { value: budget });
    await ame.connect(worker1).acceptJob(0);
    await ame.connect(worker1).submitWork(0, "ipfs://delivery");

    await expect(ame.connect(employer).releasePayment(0))
      .to.emit(ame, "PaymentReleased");

    let profile = await ame.getAgentProfile(worker1.address);
    expect(profile.reputationScore).to.equal(61n);

    await expect(ame.connect(employer).applySyntheticFeedback(0, false))
      .to.emit(ame, "FeedbackApplied");

    profile = await ame.getAgentProfile(worker1.address);
    expect(profile.reputationScore).to.equal(60n);

    await expect(ame.connect(employer).applySyntheticFeedback(0, true)).to.be.reverted;
  });

  it("decreases reputation on timeout refund", async function () {
    const { ame, owner, employer, worker1 } = await deployFixture();

    const stake = { value: ethers.parseEther("0.01") };
    await ame.connect(employer).registerAgentV2("Master", "orchestration", CATEGORY_RESEARCH, 1000, stake);
    await ame.connect(worker1).registerAgentV2("Worker", "dev", CATEGORY_DEV, 1000, stake);
    await ame.connect(owner).setAgentReputation(worker1.address, 20);

    await ame.connect(employer).createJob(worker1.address, 1, { value: ethers.parseEther("0.1") });
    await ame.connect(worker1).acceptJob(0);

    await ethers.provider.send("evm_increaseTime", [2]);
    await ethers.provider.send("evm_mine", []);

    await ame.connect(employer).refundAfterTimeout(0);
    const profile = await ame.getAgentProfile(worker1.address);
    expect(profile.reputationScore).to.equal(19n);
  });
});
