"""
TAPFed relayer_full.py
- watches DKGRegistry on Chain A
- mirrors registerRound(round, root, cid) -> Chain B
- then fetches CipherStore.getCiphers(round) on Chain A and posts missing
  postCipher(round, cid, root) -> Chain B
- idempotent: checks existing cids on Chain B and skips duplicates
- robust for web3 v7+ and older (raw_transaction vs rawTransaction)
"""

import os, json, time
from web3 import Web3

def load_abi(path):
    with open(path, "r", encoding="utf-8") as f:
        art = json.load(f)
        return art.get("abi", art)

def to_checksum(addr):
    # wrap robustly
    return Web3.to_checksum_address(addr)

def get_cids_from_cipherstore(contract, round_id):
    try:
        arr = contract.functions.getCiphers(round_id).call()
    except Exception:
        return []
    # each entry is (poster, roundId, cid, root, timestamp)
    return [entry[2] for entry in arr]

def post_cipher_if_missing(w3B, csB, private_key, round_id, cid, root, existing_set):
    if cid in existing_set:
        return None, "skip"
    sender = w3B.eth.account.from_key(private_key).address
    tx = csB.functions.postCipher(round_id, cid, root).build_transaction({
        "from": sender,
        "nonce": w3B.eth.get_transaction_count(sender),
        "gas": 500000,
        "gasPrice": w3B.eth.gas_price,
    })
    signed = w3B.eth.account.sign_transaction(tx, private_key)
    raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
    if raw is None:
        raise RuntimeError("SignedTransaction missing raw tx")
    txh = w3B.eth.send_raw_transaction(raw)
    rec = w3B.eth.wait_for_transaction_receipt(txh)
    return txh.hex(), "posted"

def main():
    print("\n=== TAPFed full relayer (DKGRegistry + CipherStore) ===\n")

    RPC_A = os.getenv("RPC_A", "http://127.0.0.1:8545")
    RPC_B = os.getenv("RPC_B", "http://127.0.0.1:8546")

    DKG_A = os.getenv("DKG_A_ADDR")
    DKG_B = os.getenv("DKG_B_ADDR")

    CIPHER_A = os.getenv("CIPHER_A_ADDR")
    CIPHER_B = os.getenv("CIPHER_B_ADDR")

    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    if not PRIVATE_KEY:
        print("ERROR: set env PRIVATE_KEY to a Chain B private key (for signing).")
        return

    w3A = Web3(Web3.HTTPProvider(RPC_A))
    w3B = Web3(Web3.HTTPProvider(RPC_B))

    print("Chain A connected?", w3A.is_connected())
    print("Chain B connected?", w3B.is_connected())

    abi_dkg = load_abi("python/abi/DKGRegistry.json")
    abi_cipher = load_abi("python/abi/CipherStore.json")

    addrA = to_checksum(DKG_A)
    addrB = to_checksum(DKG_B)
    csA_addr = to_checksum(CIPHER_A)
    csB_addr = to_checksum(CIPHER_B)

    dkgA = w3A.eth.contract(address=addrA, abi=abi_dkg)
    dkgB = w3B.eth.contract(address=addrB, abi=abi_dkg)

    csA = w3A.eth.contract(address=csA_addr, abi=abi_cipher)
    csB = w3B.eth.contract(address=csB_addr, abi=abi_cipher)

    try:
        last_seen = dkgB.functions.lastRound().call()
    except Exception:
        last_seen = 0
    print("Last round already on Chain B:", last_seen)

    sender = w3B.eth.account.from_key(PRIVATE_KEY).address
    print("Relayer sender:", sender)

    poll = int(os.getenv("RELAYER_POLL", "5"))
    backoff = int(os.getenv("RELAYER_ERROR_BACKOFF", "10"))

    while True:
        try:
            rA = dkgA.functions.lastRound().call()
            if rA > last_seen:
                print(f"\\n>>> New round on Chain A: {rA}")

                info = dkgA.functions.getRoundInfo(rA).call()
                root = info[2]
                cid = info[3]
                try:
                    root_hex = root.hex()
                except:
                    root_hex = str(root)
                print("  root:", root_hex)
                print("  cid :", cid)

                # 1) mirror registry entry to Chain B
                tx = dkgB.functions.registerRound(rA, root, cid).build_transaction({
                    "from": sender,
                    "nonce": w3B.eth.get_transaction_count(sender),
                    "gas": 800000,
                    "gasPrice": w3B.eth.gas_price,
                })
                signed = w3B.eth.account.sign_transaction(tx, PRIVATE_KEY)
                raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
                if raw is None:
                    raise RuntimeError("SignedTransaction missing raw tx")
                txh = w3B.eth.send_raw_transaction(raw)
                print("  submitted registerRound tx:", txh.hex())
                rec = w3B.eth.wait_for_transaction_receipt(txh)
                print("  registerRound mined in block", rec.blockNumber)

                # 2) mirror CipherStore entries (fetch from Chain A)
                ciphers = csA.functions.getCiphers(rA).call()
                print("  found", len(ciphers), "ciphers on Chain A for round", rA)

                existing = get_cids_from_cipherstore(csB, rA)
                existing_set = set(existing)
                print("  already on Chain B:", len(existing_set))

                for idx, entry in enumerate(ciphers):
                    poster, rr, cid_e, root_e, ts = entry
                    if cid_e in existing_set:
                        print(f"   [{idx}] skip (already on B):", cid_e)
                        continue
                    print(f"   [{idx}] posting cid ->", cid_e)
                    txh2, status = post_cipher_if_missing(w3B, csB, PRIVATE_KEY, rA, cid_e, root_e, existing_set)
                    if status == "posted":
                        print("     posted tx:", txh2)
                        # add to existing_set to avoid posting duplicates in same loop
                        existing_set.add(cid_e)
                    else:
                        print("     skipped:", cid_e)

                # 3) update last_seen after successful mirror
                last_seen = rA
                print("  round", rA, "mirrored successfully.")

        except Exception as e:
            print("Error in relayer loop:", e)
            time.sleep(backoff)
            continue

        time.sleep(poll)

if __name__ == "__main__":
    main()
