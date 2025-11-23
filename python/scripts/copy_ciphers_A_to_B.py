# copy_ciphers_A_to_B.py
import os, time, json
from web3 import Web3

RPC_A = os.environ.get('RPC_A','http://127.0.0.1:8545')
RPC_B = os.environ.get('RPC_B','http://127.0.0.1:8546')
CIPHER_A = os.environ.get('CIPHER_A_ADDR')
CIPHER_B = os.environ.get('CIPHER_B_ADDR')
ROUND = int(os.environ.get('ROUND','6'))
PK = os.environ.get('PRIVATE_KEY')
if not PK:
    raise SystemExit("Set PRIVATE_KEY in env before running.")

A = Web3(Web3.HTTPProvider(RPC_A))
B = Web3(Web3.HTTPProvider(RPC_B))
abi = json.load(open('python/abi/CipherStore.json','r',encoding='utf-8'))['abi']
cA = A.eth.contract(address=A.to_checksum_address(CIPHER_A), abi=abi)
cB = B.eth.contract(address=B.to_checksum_address(CIPHER_B), abi=abi)

ciphers = cA.functions.getCiphers(ROUND).call()
print('Found', len(ciphers), 'ciphers on Chain A for round', ROUND)

import time
# ... (existing imports and setup)

acct = B.eth.account.from_key(PK)
sender = acct.address
nonce = B.eth.get_transaction_count(sender)
gasprice = B.eth.gas_price
chainid = B.eth.chain_id

for idx, entry in enumerate(ciphers):
    poster, rid, cid, root, ts = entry
    print('Posting', idx, 'cid=', cid, 'root=', root, 'rid=', rid)
    tx = cB.functions.postCipher(rid, cid, root).build_transaction({
        'from': sender,
        'nonce': nonce,
        'gas': 300000,
        'gasPrice': gasprice,
        'chainId': chainid
    })
    signed = acct.sign_transaction(tx)
    # robust lookup for raw transaction bytes (v6 vs v5)
    raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
    if raw is None:
        raise RuntimeError("Couldn't find raw transaction bytes on SignedTransaction object")
    txh = B.eth.send_raw_transaction(raw)
    print('submitted tx', txh.hex())
    r = B.eth.wait_for_transaction_receipt(txh, timeout=120)
    print('receipt status', r.status, 'logs', len(r.logs))
    nonce += 1
    time.sleep(0.3)


print('Done.')
