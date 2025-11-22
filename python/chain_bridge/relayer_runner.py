"""
Fixed TAPFed cross-chain relayer for modern web3:
- uses signed.raw_transaction (snake_case) to work with web3 v7+
- updates last_seen only after successful receipt
- backoff on errors to avoid tight repeat loops
"""

import os
import json
import time
from web3 import Web3


def load_abi(path):
    with open(path, "r", encoding="utf-8") as f:
        art = json.load(f)
        return art.get("abi", art)


def main():
    print("\n=== TAPFed Cross-Chain Relayer (fixed) ===\n")

    RPC_A = os.getenv("RPC_A", "http://127.0.0.1:8545")
    RPC_B = os.getenv("RPC_B", "http://127.0.0.1:8546")

    DKG_A = os.getenv("DKG_A_ADDR")
    DKG_B = os.getenv("DKG_B_ADDR")

    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    if not PRIVATE_KEY:
        print("ERROR: Set $env:PRIVATE_KEY to a Chain B private key.")
        return

    w3A = Web3(Web3.HTTPProvider(RPC_A))
    w3B = Web3(Web3.HTTPProvider(RPC_B))

    print("Chain A connected?", w3A.is_connected())
    print("Chain B connected?", w3B.is_connected())

    abi_dkg = load_abi("python/abi/DKGRegistry.json")

    # use Web3.to_checksum_address to be robust
    addrA = Web3.to_checksum_address(DKG_A)
    addrB = Web3.to_checksum_address(DKG_B)

    contractA = w3A.eth.contract(address=addrA, abi=abi_dkg)
    contractB = w3B.eth.contract(address=addrB, abi=abi_dkg)

    try:
        last_seen = contractB.functions.lastRound().call()
    except Exception:
        last_seen = 0
    print("Last round already on Chain B:", last_seen)

    acct = w3B.eth.account.from_key(PRIVATE_KEY)
    sender = acct.address
    print("Using relayer sender:", sender)

    poll_interval = int(os.getenv("RELAYER_POLL", "5"))
    error_backoff = int(os.getenv("RELAYER_ERROR_BACKOFF", "10"))

    while True:
        try:
            rA = contractA.functions.lastRound().call()

            if rA > last_seen:
                print(f"\n>>> New round detected on Chain A: {rA}")

                info = contractA.functions.getRoundInfo(rA).call()
                root = info[2]
                cid = info[3]

                try:
                    root_hex = root.hex()
                except Exception:
                    root_hex = str(root)

                print("  mirroring root:", root_hex)
                print("  mirroring cid:", cid)

                tx = contractB.functions.registerRound(
                    rA, root, cid
                ).build_transaction({
                    "from": sender,
                    "nonce": w3B.eth.get_transaction_count(sender),
                    "gas": 800000,
                    "gasPrice": w3B.eth.gas_price,
                })

                signed = w3B.eth.account.sign_transaction(tx, PRIVATE_KEY)

                # web3 v7+ SignedTransaction uses .raw_transaction (snake_case)
                raw = getattr(signed, "raw_transaction", None)
                if raw is None:
                    # fallback: try camelCase name (older web3)
                    raw = getattr(signed, "rawTransaction", None)

                if raw is None:
                    raise RuntimeError("SignedTransaction has no raw transaction attribute")

                tx_hash = w3B.eth.send_raw_transaction(raw)
                print("  submitted tx:", tx_hash.hex())

                receipt = w3B.eth.wait_for_transaction_receipt(tx_hash)
                print("  mined in block:", receipt.blockNumber)

                # update last_seen only after successful receipt
                last_seen = rA

        except Exception as e:
            print("Error:", e)
            # sleep longer after errors to avoid tight repeated failures
            time.sleep(error_backoff)
            continue

        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
