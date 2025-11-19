import "@nomiclabs/hardhat-ethers";

export default {
  solidity: "0.8.19",
  networks: {
    hardhat: { chainId: 1337 },
    chainA: {
      url: "http://127.0.0.1:8545",
      chainId: 1337
    },
    chainB: {
      url: "http://127.0.0.1:8546",
      chainId: 1338
    }
  }
};
