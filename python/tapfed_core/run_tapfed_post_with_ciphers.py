#!/usr/bin/env python3
"""
run_tapfed_post_with_ciphers.py

Full poster script for TAPFed demo:
 - builds demo participants (SimpleModel)
 - uploads encrypted objects to local_ipfs_store (upload_json)
 - builds Merkle tree and root
 - registers the round on Chain A (DKGRegistry)
 - posts each cipher to Chain A's CipherStore (postCipher)

Environment variables:
 - RPC_A          (default: http://127.0.0.1:8545)
 - DKG_A_ADDR     (required) address of DKGRegistry on Chain A
 - CIPHER_A_ADDR  (required) address of CipherStore on Chain A
 - ROUND          optional: round id (int). If absent, this script will try to compute a safe next id.
 - PRIVATE_KEY    optional: if set, will sign and broadcast txs (recommended when using an unlocked node this can be omitted)
 - PYTHONPATH     ensure it includes repo/python (or run from repo root with PYTHONPATH set)

This script is written to be resilient across web3 versions (uses is_connected/is_connected()).
"""

import os
import json
import time
from web3 import Web3
from eth_account import Account

# repo modules
from tapfed_core.model import SimpleModel
from tapfed_core.enc import ec_encrypt_scalar
from proofs.mk_tree import MerkleTree
from utils.ipfs_client import upload_json

# helper: load ABI JSON (handles artifact or plain ABI)
def load_abi(path):
    with open(path, "r", encoding="utf-8") as f:
        art = json.load(f)
    return art.get("abi", art)

# env / defaults
RPC_A = os.getenv("RPC_A", "http://127.0.0.1:8545")
DKG_A_ADDR = os.getenv("DKG_A_ADDR", "").strip()
CIPHER_A_ADDR = os.getenv("CIPHER_A_ADDR", "").strip()
ROUND_ENV = os.getenv("ROUND", None)
PRIVATE_KEY = os.getenv("PRIVATE_KEY", None)

if DKG_A_ADDR == "" or CIPHER_A_ADDR == "":
    print("ERROR: Set DKG_A_ADDR and CIPHER_A_ADDR environment variables.")
    raise SystemExit(1)

# web3 connection
w3 = Web3(Web3.HTTPProvider(RPC_A))
print("Connecting to RPC:", RPC_A)
if not w3.is_connected():
    print("ERROR: cannot connect to RPC:", RPC_A)
    raise SystemExit(1)

# canonical addresses
dkg_addr = w3.to_checksum_address(DKG_A_ADDR)
cipher_addr = w3.to_checksum_address(CIPHER_A_ADDR)

# load ABIs
here = os.path.dirname(__file__) or "."
abi_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "abi")
# fallback paths
dkg_abi_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "abi", "DKGRegistry.json")
cipher_abi_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "abi", "CipherStore.json")

if not os.path.exists(dkg_abi_path) or not os.path.exists(cipher_abi_path):
    # attempt relative to repo root
    dkg_abi_path = "python/abi/DKGRegistry.json"
    cipher_abi_path = "python/abi/CipherStore.json"

dkg_abi = load_abi(dkg_abi_path)
cipher_abi = load_abi(cipher_abi_path)

dkg_contract = w3.eth.contract(address=dkg_addr, abi=dkg_abi)
cipher_contract = w3.eth.contract(address=cipher_addr, abi=cipher_abi)

# signer (if PRIVATE_KEY present)
acct = None
if PRIVATE_KEY:
    acct = Account.from_key(PRIVATE_KEY)
    print("Using PRIVATE_KEY -> sender:", acct.address)
else:
    # fallback: use first unlocked account if available
    try:
        acct = Account.from_key(None)  # will fail intentionally
    except Exception:
        # if node has unlocked accounts, Web3 can use them via transactions without signing in code.
        acct = None
        print("No PRIVATE_KEY provided - will attempt node-local transact (if node unlocked).")

# helper to build, sign, and send tx or use transact directly if node has unlocked account
def send_tx(fn, tx_kwargs=None):
    """
    fn: contract function object (.build_transaction)
    tx_kwargs: additional transaction fields (gas, gasPrice, etc.)
    Returns tx hash hex.
    """
    if tx_kwargs is None:
        tx_kwargs = {}
    if PRIVATE_KEY:
        # build transaction, sign then send_raw_transaction
        # prepare base tx params
        sender = acct.address
        nonce = w3.eth.get_transaction_count(sender)
        # estimate gas
        try:
            est = fn.estimate_gas({"from": sender})
        except Exception:
            est = 200000
        tx = fn.build_transaction({
            "from": sender,
            "nonce": nonce,
            "gas": est + 20000,
            "gasPrice": w3.eth.gas_price,
            **tx_kwargs
        })
        signed = acct.sign_transaction(tx)
        raw = signed.raw_transaction
        txh = w3.eth.send_raw_transaction(raw)
        print("Submitted signed tx:", txh.hex())
        receipt = w3.eth.wait_for_transaction_receipt(txh)
        print("Mined in block:", receipt.blockNumber)
        return txh.hex()
    else:
        # try node-local transact (may only work if node unlocked)
        try:
            txh = fn.transact(tx_kwargs or {})
            # if transact returned tx hash in some web3 impls:
            if isinstance(txh, (bytes, bytearray)):
                txh_hex = w3.to_hex(txh)
            else:
                txh_hex = txh
            # wait
            try:
                receipt = w3.eth.wait_for_transaction_receipt(txh_hex)
                print("Mined in block:", receipt.blockNumber)
            except Exception:
                pass
            print("Submitted tx (node):", txh_hex)
            return txh_hex
        except Exception as e:
            print("transact() failed and no PRIVATE_KEY provided. Error:", e)
            raise

# determine round id
def compute_next_round():
    try:
        last = dkg_contract.functions.lastRound().call()
        return last + 1
    except Exception:
        return 1

round_id = int(ROUND_ENV) if ROUND_ENV is not None else compute_next_round()
print("Using round id:", round_id)

# 1) build demo participants, encrypt values and upload
participants = []
cids = []
enc_objs = []
ciphers_bytes = []

NUM_PARTICIPANTS = 3

for i in range(NUM_PARTICIPANTS):
    m = SimpleModel()
    # set bias as in demo
    m.fc2.bias.data.fill_(0.1 * (i + 1))
    participants.append(m)

for i, p in enumerate(participants):
    val = float(p.fc2.bias.data[0].item())
    enc = ec_encrypt_scalar(None, val)
    obj = {"participant": i, "enc": enc}
    cid = upload_json(obj)
    cids.append(cid)
    enc_objs.append(enc)
    ciphers_bytes.append(json.dumps(obj).encode())
    print(f"Uploaded participant {i}: bias={val} -> {cid}")

# 2) build merkle root
mt = MerkleTree(ciphers_bytes)
root = mt.root()
print("Merkle root (hex):", root.hex())

# 3) register round on Chain A (DKGRegistry.registerRound)
# prepare metadataCID: pick the "first" CID or construct a manifest; we use first for demo
metadata_cid = cids[0] if cids else ""
print("Posting round -> dkg.registerRound(roundId, root, metadataCID)")

try:
    reg_fn = dkg_contract.functions.registerRound(round_id, root, metadata_cid)
    txh = send_tx(reg_fn)
    # try to read back
    try:
        info = dkg_contract.functions.getRoundInfo(round_id).call()
        print("On-chain round info:", info)
    except Exception as e:
        print("Could not read round info after post:", e)
except Exception as e:
    print("registerRound failed:", e)
    # continue to attempt posting ciphers (maybe round already exists)

# 4) Post ciphers into Chain A's CipherStore (postCipher(roundId, cid, root))
print("Posting individual ciphers to CipherStore on Chain A...")
posted = []
for idx, cid in enumerate(cids):
    try:
        post_fn = cipher_contract.functions.postCipher(round_id, cid, root)
        txh = send_tx(post_fn)
        posted.append((idx, cid, txh))
    except Exception as e:
        print(f"Failed to post cipher {idx} cid={cid} ->", e)

if posted:
    print("Posted ciphers:", posted)
else:
    print("No ciphers posted on-chain (either failed or they already exist).")

# final verification: read CipherStore.getCiphers(round)
try:
    remote_ciphers = cipher_contract.functions.getCiphers(round_id).call()
    print("Chain A getCiphers({}) ->".format(round_id), remote_ciphers)
except Exception as e:
    print("Could not fetch ciphers from Chain A:", e)

print("Done.")
