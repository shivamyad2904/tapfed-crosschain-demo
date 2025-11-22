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

![TAPFed Architecture](/mnt/data/tapfed_architecture.png)

The TAPFed pipeline consists of three major components:

1. **Clients** performing local model updates.
2. **Aggregator** producing encrypted contributions.
3. **Blockchain (DKG + FE)** storing encrypted values and verifying rounds.

---

## 3. Cross‑Chain Event Flow

![Cross Chain Flow](/mnt/data/cross_chain_flow.png)

Workflow:

1. Round and cipher data is posted on **Chain A**.
2. Relayer monitors Chain A using Web3 event filters.
3. Relayer mirrors:

   * `registerRound` → to DKGRegistry on Chain B
   * `storeCipher` → to CipherStore on Chain B
4. Chain B becomes a synchronized mirror.

---

## 4. DKG + FE Workflow

![DKG FE Workflow](/mnt/data/dkg_fe_workflow.png)

Detailed Steps:

1. **DKG** creates distributed private key shares.
2. **Functional Encryption** encrypts the `fc2.bias` vector.
3. **Aggregation** decrypts FE ciphertexts to compute a global sum.
4. FE decrypt ensures **privacy**, and DKG ensures **no single party has the key**.

---

## 5. Repository Structure

![Folder Structure](/mnt/data/folder_structure.png)

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

* Implemented enhanced `run_tapfed_post_with_ciphers.py` which:

  * Uploads encrypted ciphers
  * Computes Merkle root
  * Posts round via signed transaction
  * Posts individual ciphers
  * Verifies storage

### ✔ Relayer Working (DKGRegistry)

* Successfully mirrored **round registrations** to Chain B.
* Verified using `verify_dkg_chainb.py`.

---

## 7. Current Issue (as of last logs)

Even though rounds mirror correctly:

* **CipherStore on Chain B is not receiving ciphers.**
* Chain B always returns: `getCiphers(round) = []`.
* Yet Chain A stores ciphers normally.

This indicates the relayer is:

* **Not detecting CipherStore events** OR
* **Calling Chain B’s CipherStore incorrectly**.

Diagnosis so far:

* ABI verified
* Contract address correct
* Web3 connection working
* No logs found in transaction receipts

Next step is to patch the relayer to explicitly subscribe to `CipherStored` and forward them.

---

## 8. What Remains

### 🔧 **Remaining Tasks:**

1. **Fix CipherStore mirroring** — ensure `CipherStored(cid)` appears on Chain B.
2. **Modify relayer** to:

   * Listen specifically to `CipherStored` events on Chain A
   * Pass `{ roundId, cid }` to Chain B
3. **Add event decoding debugging**
4. **Add replay protection** to avoid duplicate writes
5. **Add `lastMirroredRound` tracking** for CipherStore
6. **Stress test with multiple rounds** (2 → 10 rounds)
7. **Generate final FE-based aggregated bias** from cross‑chain verification
8. **Final reporting + screenshots** for thesis

---

## 9. Academic Contributions

This project demonstrates:

* **A novel cross‑chain synchronization approach for federated learning.**
* **Secure encryption layer using FE**.
* **Threshold cryptography via DKG**.
* **Auditable ML aggregation on blockchain**.


---

## 10. Contacts

Maintainer: **Shivam Yadav** (IIIT Guwahati)
Email: *[shivam.yadav24m@iiitg.ac.in](mailto:shivam.yadav24m@iiitg.ac.in)*


