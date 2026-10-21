const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("StakingRewards Permit2", function () {
  let stakingRewards, stakingToken, rewardToken;
  let owner, staker;

  beforeEach(async function () {
    [owner, staker] = await ethers.getSigners();

    const StakingToken = await ethers.getContractFactory("StakingToken");
    stakingToken = await StakingToken.deploy();
    await stakingToken.waitForDeployment();

    const RewardToken = await ethers.getContractFactory("RewardToken");
    rewardToken = await RewardToken.deploy();
    await rewardToken.waitForDeployment();

    const StakingRewards = await ethers.getContractFactory("StakingRewards");
    stakingRewards = await StakingRewards.deploy(
      await stakingToken.getAddress(),
      await rewardToken.getAddress()
    );
    await stakingRewards.waitForDeployment();

    await stakingToken.mint(staker.address, ethers.parseEther("1000"));
    await rewardToken.mint(await stakingRewards.getAddress(), ethers.parseEther("10000"));
  });

  it("exposes canonical Permit2 address", async function () {
    expect(await stakingRewards.PERMIT2()).to.equal(
      "0x000000000022D473030F116dDEE9F6B43aC78BA3"
    );
  });

  it("fallback approve flow still works", async function () {
    const amount = ethers.parseEther("100");
    await stakingToken.connect(staker).approve(await stakingRewards.getAddress(), amount);
    await stakingRewards.connect(staker).stake(amount);
    expect(await stakingRewards.balanceOf(staker.address)).to.equal(amount);
  });

  it("stakeWithPermit reverts without valid Permit2 signature", async function () {
    const amount = ethers.parseEther("100");
    await expect(
      stakingRewards.connect(staker).stakeWithPermit(
        amount,
        0,
        Math.floor(Date.now() / 1000) + 3600,
        "0x"
      )
    ).to.be.reverted;
  });
});
