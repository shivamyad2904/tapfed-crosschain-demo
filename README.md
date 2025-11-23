# TAPFed Cross-Chain Demo README

## 1. Overview

This repository implements a **full TAPFed (Threshold Aggregation Protocol for Federated Learning)** system extended with **cross‑chain replication** using a relayer. The system combines:

* **Decentralized Key Generation (DKG)** for threshold key shares
* **Functional Encryption (FE)** applied only to `fc2.bias`
* **Federated Learning aggregation** with secure bias masking
* **Cross‑chain mirroring** of DKGRegistry and CipherStore events

It simulates a dual‑chain setup:

* **Chain A** — main TAPFed chain (training, encryption, posting rounds)
* **Chain B** — read‑only mirror, used to validate cross‑chain replication

---

## 2. System Architecture

![TAPFed Architecture](docs/images/tapfed_architecture.png)

High level components:

1. **Clients** performing local model updates.
2. **Aggregator** producing encrypted contributions.
3. **Blockchain (DKG + FE)** storing encrypted values and verifying rounds.

---

## 3. Cross‑Chain Event Flow

![Cross Chain Flow](docs/images/cross_chain_flow.png)

Workflow:

1. Round and cipher data is posted on **Chain A**.
2. Relayer monitors Chain A using Web3 event filters.
3. Relayer mirrors:

   * `registerRound` → to DKGRegistry on Chain B
   * `storeCipher` → to CipherStore on Chain B
4. Chain B becomes a synchronized mirror for both registry and ciphers.

---

## 4. DKG + FE Workflow

![DKG FE Workflow](docs/images/dkg_fe_workflow.png)

Detailed Steps:

1. **DKG** creates distributed private key shares.
2. **Functional Encryption** encrypts the `fc2.bias` vector per participant.
3. **Aggregator** posts a Merkle root and individual cipher entries (CID + root) on Chain A. 
4. **Relayer** forwards on-chain entries to Chain B for auditability.
5. **Aggregation** decrypts FE ciphertexts to compute a global sum.
6. FE decrypt ensures **privacy**, and DKG ensures **no single party has the key**.

---

## 5. Repository Structure

![Folder Structure](docs/images/folder_structure.png)

```
tapfed-crosschain-demo/
│
├── contracts/              # Solidity smart contracts
│   ├── DKGRegistry.sol
│   ├── CipherStore.sol
│   ├── TAPFedCore.sol
│
├── python/                 # Python TAPFed engine + relayer
│   ├── chain_bridge/       # Relayer files
│   ├── tapfed_core/        # Training, encryption, round posting
│   ├── proofs/             # Optional crypto utilities
│   ├── utils/              # Helper functions
│   └── scripts/            # Debugging + verification tools
│
├── foundry/                # Hardhat/Foundry deployment
├── scripts/                # JS deployment utilities
└── local_ipfs_store/       # Local simulation of IPFS storage
```

---

## 6. What We Have Achieved

### ✔ Smart Contract Deployment

* Deployed **DKGRegistry** and **CipherStore** on **Chain A and Chain B**.
* Verified correct contract bytecode on both chains.

### ✔ Poster Script Working

`run_tapfed_post_with_ciphers.py`:
* Uploads encrypted ciphers to `local_ipfs_store/` (simulated IPFS).
* Computes Merkle root for the round.
* Posts `registerRound(roundId, root, metadataCID)` on Chain A.
* Posts individual `postCipher(roundId, cid, root)` transactions on Chain A.

### ✔ Relayer Working (DKGRegistry)

* Relayer mirrors `registerRound` events from Chain A → Chain B.
* Verified `lastRound` consistent on both chains.

---
## 7. How to Run the Demo

1. **Start two Anvil/Hardhat nodes (Chain A and Chain B)**

    * (Run two terminals, each running anvil/hardhat on different RPC ports, e.g. 8545 and 8546.)

2. **Deploy contracts**

    * (using Foundry/Hardhat scripts)

3. **Post a round (Chain A)**

`python python/tapfed_core/run_tapfed_post_with_ciphers.py`

4. **Start the relayer**

`python python/chain_bridge/relayer_full.py`

5. **Verify ciphers**

`python python/scripts/verify_ciphers.py`

---

## 8. Academic Contributions

This project demonstrates:

* **A novel cross‑chain synchronization approach for federated learning.**
* **Secure encryption layer using FE**.
* **Threshold cryptography via DKG**.
* **Auditable ML aggregation on blockchain**.


---

## 9. Contacts

Maintainer: **Shivam Yadav** (IIIT Guwahati)
Email: *[shivam.yadav24m@iiitg.ac.in](mailto:shivam.yadav24m@iiitg.ac.in)*


