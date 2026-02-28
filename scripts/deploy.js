const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const networkName = hre.network.name;
  const feeBps = Number(process.env.PLATFORM_FEE_BPS || "100");
  const version = (process.env.AME_CONTRACT_VERSION || "v1").trim().toLowerCase();
  const minStakeWei = process.env.MIN_REGISTRATION_STAKE_WEI || "0";
  const contractName = version === "v2" ? "AgenticMonadEconomyV2" : "AgenticMonadEconomy";

  console.log("Deploying from:", deployer.address);
  console.log("Network:", networkName);
  console.log("Contract version:", version);

  const Factory = await hre.ethers.getContractFactory(contractName);
  const contract =
    contractName === "AgenticMonadEconomyV2"
      ? await Factory.deploy(feeBps, minStakeWei)
      : await Factory.deploy(feeBps);
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log(contractName, "deployed at:", address);

  const artifact = await hre.artifacts.readArtifact(contractName);
  const outDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const outFile = path.join(outDir, `${networkName}.json`);
  const payload = {
    network: networkName,
    chainId: Number((await hre.ethers.provider.getNetwork()).chainId),
    version,
    contract: contractName,
    address,
    deployedAt: new Date().toISOString(),
    abi: artifact.abi
  };

  fs.writeFileSync(outFile, JSON.stringify(payload, null, 2), "utf8");
  console.log("Deployment artifact written:", outFile);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
