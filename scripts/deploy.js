const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const networkName = hre.network.name;
  const feeBps = 100; // 1%

  console.log("Deploying from:", deployer.address);
  console.log("Network:", networkName);

  const Factory = await hre.ethers.getContractFactory("AgenticMonadEconomy");
  const contract = await Factory.deploy(feeBps);
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("AgenticMonadEconomy deployed at:", address);

  const artifact = await hre.artifacts.readArtifact("AgenticMonadEconomy");
  const outDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const outFile = path.join(outDir, `${networkName}.json`);
  const payload = {
    network: networkName,
    chainId: Number((await hre.ethers.provider.getNetwork()).chainId),
    contract: "AgenticMonadEconomy",
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
