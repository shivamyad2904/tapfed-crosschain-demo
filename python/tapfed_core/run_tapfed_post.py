"""
Fixed run_tapfed_post script for TAPFed demo.
- Respects environment variable DKG_A_ADDR (required)
- Uses RPC from RPC_A (default http://127.0.0.1:8545)
- Uses PRIVATE_KEY if present, otherwise attempts an unlocked account via web3.eth.default_account or first account
- Robust to web3 API name changes (is_connected/to_checksum_address/build_transaction vs buildTransaction)
- Logs useful information and raises clear errors

Save this file as python/tapfed_core/run_tapfed_post.fixed.py and run with:

  $env:RPC_A = "http://127.0.0.1:8545"
  $env:DKG_A_ADDR = "0x..."            # REQUIRED
  $env:PRIVATE_KEY = "0x..."          # optional (use for signing)
  python python/tapfed_core/run_tapfed_post.fixed.py

"""
import os
import json
import time
import sys
from web3 import Web3

# helpers for compatibility
def is_connected(w3):
    return getattr(w3, 'is_connected', None) and w3.is_connected() or getattr(w3, 'isConnected', None) and w3.isConnected()

def to_checksum(w3, addr):
    if getattr(w3, 'to_checksum_address', None):
        return w3.to_checksum_address(addr)
    return getattr(w3, 'toChecksumAddress')(addr)

# load envs
RPC = os.getenv('RPC_A', 'http://127.0.0.1:8545')
DKG_ADDR = os.getenv('DKG_A_ADDR')
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
ROUND = int(os.getenv('ROUND', '1'))

if not DKG_ADDR:
    print('ERROR: DKG_A_ADDR environment variable is not set. Set it to the deployed DKGRegistry address.')
    sys.exit(1)

print('Connecting to RPC:', RPC)
w3 = Web3(Web3.HTTPProvider(RPC))
if not is_connected(w3):
    print('ERROR: could not connect to RPC at', RPC)
    sys.exit(1)

# pick sender
if PRIVATE_KEY:
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    sender = acct.address
    print('Using PRIVATE_KEY -> sender:', sender)
else:
    # try default account / first account
    try:
        accounts = w3.eth.accounts
    except Exception:
        accounts = []
    if accounts:
        sender = accounts[0]
        print('Using unlocked account sender:', sender)
    else:
        print('ERROR: No PRIVATE_KEY set and node reports no unlocked accounts. Set PRIVATE_KEY env var.')
        sys.exit(1)

# load ABI
abi_path = os.path.join(os.path.dirname(__file__), '..', 'abi', 'DKGRegistry.json')
# fallback to repository layout
if not os.path.exists(abi_path):
    abi_path = os.path.join(os.getcwd(), 'python', 'abi', 'DKGRegistry.json')

with open(abi_path, 'r', encoding='utf-8') as f:
    art = json.load(f)
abi = art.get('abi', art)

dkg_address = to_checksum(w3, DKG_ADDR)
contract = w3.eth.contract(address=dkg_address, abi=abi)

print('Prepared contract at', dkg_address)

# build demo ciphers and merkle root using provided local helper if available
# For compatibility we attempt to import the project's utilities; if not available we fallback to demo values
try:
    from tapfed_core.model import SimpleModel
    from tapfed_core.enc import ec_encrypt_scalar, ec_add_ciphertexts
    from proofs.mk_tree import MerkleTree
    from utils.ipfs_client import upload_json
    # create demo participants (small deterministic demo)
    parts = []
    for i in range(3):
        m = SimpleModel()
        m.fc2.bias.data.fill_(0.1 * (i+1))
        parts.append(m)

    cids = []
    enc_objs = []
    ciphers_bytes = []
    for i, p in enumerate(parts):
        val = float(p.fc2.bias.data[0].item())
        enc = ec_encrypt_scalar(None, val)
        obj = {'participant': i, 'enc': enc}
        cid = upload_json(obj)
        cids.append(cid)
        enc_objs.append(enc)
        ciphers_bytes.append(json.dumps(obj).encode())

    mt = MerkleTree(ciphers_bytes)
    root = mt.root()
    metadataCID = cids[0] if cids else ''
    print('Merkle root (hex):', root.hex())
except Exception as e:
    # fallback demo values
    print('Could not import project helpers; using fallback demo values (no IPFS). Error:', e)
    root = bytes.fromhex('18b2f6b5531a05a6e4518e9fce884d4681070999dc587d2ece34886e32c0f39d')
    metadataCID = 'local_ipfs_store\\obj_demo.json'

# Try to post the round
try:
    print('Posting round -> dkg.registerRound(roundId, root, metadataCID)')
    fn = contract.functions.registerRound(ROUND, root, metadataCID)

    # If node supports unlocked accounts use transact
    if not PRIVATE_KEY and getattr(fn, 'transact', None):
        try:
            txh = fn.transact({'from': sender})
            print('Posted (transact) round tx:', txh.hex())
            # wait for receipt
            r = w3.eth.wait_for_transaction_receipt(txh)
            print('Mined in block:', r.blockNumber)
        except Exception as e:
            print('transact() failed:', e)
            raise
    else:
        # build transaction (handle both build_transaction and buildTransaction names)
        nonce = w3.eth.get_transaction_count(sender)
        tx = None
        try:
            tx = fn.build_transaction({
                'from': sender,
                'nonce': nonce,
                'maxPriorityFeePerGas': w3.to_wei('1', 'gwei'),
                'maxFeePerGas': w3.to_wei('200', 'gwei'),
            })
        except Exception:
            try:
                tx = fn.buildTransaction({
                    'from': sender,
                    'nonce': nonce,
                    'gasPrice': w3.to_wei('20', 'gwei'),
                })
            except Exception as e:
                print('Could not build transaction via build_transaction/buildTransaction:', e)
                raise

        # sign and send
        signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        raw = signed.rawTransaction if hasattr(signed, 'rawTransaction') else signed.raw_transaction
        txh = w3.eth.send_raw_transaction(raw)
        print('Submitted signed tx:', txh.hex())
        r = w3.eth.wait_for_transaction_receipt(txh)
        print('Mined in block:', r.blockNumber)

    # try to read back round info
    try:
        info = contract.functions.getRoundInfo(ROUND).call()
        print('On-chain round info:', info)
    except Exception as e:
        print('Could not read round info after post:', e)

except Exception as e:
    print('Error while posting round:', e)

# optionally, you can also post individual ciphers to CipherStore using similar logic (not included here)
print('Done.')
