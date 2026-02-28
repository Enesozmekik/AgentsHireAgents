const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("AgenticMonadEconomy", function () {
  async function deployFixture() {
    const [owner, employer, worker, other] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("AgenticMonadEconomy");
    const ame = await Factory.deploy(100); // 1% fee
    await ame.waitForDeployment();
    return { ame, owner, employer, worker, other };
  }

  it("runs open -> taken -> submitted -> resolved flow", async function () {
    const { ame, employer, worker } = await deployFixture();

    await ame.connect(employer).registerAgent("Master", "orchestration");
    await ame.connect(worker).registerAgent("Worker", "execution");

    const budget = ethers.parseEther("1");
    await ame.connect(employer).createJob(worker.address, 3600, { value: budget });

    expect(await ame.lockedFunds()).to.equal(budget);

    await ame.connect(worker).acceptJob(0);
    await ame.connect(worker).submitWork(0, "ipfs://demo-delivery");

    const workerBalanceBefore = await ethers.provider.getBalance(worker.address);
    const tx = await ame.connect(employer).approveWork(0);
    await tx.wait();
    const workerBalanceAfter = await ethers.provider.getBalance(worker.address);

    const expectedPayout = (budget * 9900n) / 10000n;
    expect(workerBalanceAfter - workerBalanceBefore).to.equal(expectedPayout);

    const job = await ame.getJob(0);
    expect(job.status).to.equal(3n);
    expect(await ame.lockedFunds()).to.equal(0n);
  });

  it("allows refund after timeout", async function () {
    const { ame, employer, worker } = await deployFixture();

    await ame.connect(employer).registerAgent("Master", "orchestration");
    await ame.connect(worker).registerAgent("Worker", "execution");

    const budget = ethers.parseEther("0.5");
    await ame.connect(employer).createJob(worker.address, 1, { value: budget });
    await ame.connect(worker).acceptJob(0);

    await ethers.provider.send("evm_increaseTime", [2]);
    await ethers.provider.send("evm_mine", []);

    await expect(ame.connect(employer).refundAfterTimeout(0))
      .to.emit(ame, "JobRefunded")
      .withArgs(0, employer.address, budget);

    const job = await ame.getJob(0);
    expect(job.status).to.equal(4n);
    expect(await ame.lockedFunds()).to.equal(0n);
  });

  it("blocks unregistered callers", async function () {
    const { ame, employer, worker, other } = await deployFixture();

    await ame.connect(employer).registerAgent("Master", "orchestration");
    await ame.connect(worker).registerAgent("Worker", "execution");
    await ame.connect(employer).createJob(worker.address, 60, { value: ethers.parseEther("0.2") });

    await expect(ame.connect(other).acceptJob(0)).to.be.reverted;
  });

  it("blocks reentrancy on withdrawFees", async function () {
    const { ame, owner } = await deployFixture();

    const AttackerFactory = await ethers.getContractFactory("ReentrantWithdrawAttacker");
    const attacker = await AttackerFactory.connect(owner).deploy(await ame.getAddress());
    await attacker.waitForDeployment();

    await ame.connect(owner).transferOwnership(await attacker.getAddress());

    const donation = ethers.parseEther("1");
    await owner.sendTransaction({ to: await ame.getAddress(), value: donation });

    const withdrawAmount = ethers.parseEther("0.4");
    await attacker.connect(owner).attack(withdrawAmount);

    const drained = await ethers.provider.getBalance(await attacker.getAddress());
    expect(drained).to.equal(withdrawAmount);
  });

  it("enforces owner-only fee controls", async function () {
    const { ame, owner, employer, worker, other } = await deployFixture();

    await expect(ame.connect(other).setPlatformFeeBps(200)).to.be.reverted;
    await expect(ame.connect(other).transferOwnership(other.address)).to.be.reverted;
    await expect(ame.connect(other).withdrawFees(other.address, 1)).to.be.reverted;

    await ame.connect(owner).setPlatformFeeBps(200);
    expect(await ame.platformFeeBps()).to.equal(200n);

    await expect(ame.connect(owner).setPlatformFeeBps(1001)).to.be.reverted;

    await ame.connect(employer).registerAgent("Master", "orchestration");
    await ame.connect(worker).registerAgent("Worker", "execution");
    await ame.connect(employer).createJob(worker.address, 3600, { value: ethers.parseEther("1") });
    await ame.connect(worker).acceptJob(0);
    await ame.connect(worker).submitWork(0, "ipfs://delivery");
    await ame.connect(employer).approveWork(0);

    // 2% fee over 1 ether = 0.02 ether available as protocol fee.
    const feeAmount = ethers.parseEther("0.02");
    const ownerBalanceBefore = await ethers.provider.getBalance(owner.address);
    const tx = await ame.connect(owner).withdrawFees(owner.address, feeAmount);
    const receipt = await tx.wait();
    const ownerBalanceAfter = await ethers.provider.getBalance(owner.address);

    const gasPrice = receipt.gasPrice ?? tx.gasPrice ?? 0n;
    const gasCost = receipt.gasUsed * gasPrice;
    expect(ownerBalanceAfter + gasCost - ownerBalanceBefore).to.equal(feeAmount);
  });
});
