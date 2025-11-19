import hre from "hardhat";

async function main() {
  const DKG = await hre.ethers.getContractFactory("DKGRegistry");
  const dkg = await DKG.deploy();
  await dkg.deployed();
  console.log("DKGRegistry deployed to:", dkg.address);

  const CS = await hre.ethers.getContractFactory("CipherStore");
  const cs = await CS.deploy();
  await cs.deployed();
  console.log("CipherStore deployed to:", cs.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
