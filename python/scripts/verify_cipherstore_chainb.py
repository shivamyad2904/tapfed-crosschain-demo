import json
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8546"))
with open("python/abi/CipherStore.json","r",encoding="utf-8") as f:
    art = json.load(f)
abi = art.get("abi", art)
cs_addr = "0x71C95911E9a5D330f4D621842EC243EE1343292e"
contract = w3.eth.contract(address=w3.to_checksum_address(cs_addr), abi=abi)
ciphers = contract.functions.getCiphers(1).call()
print("Ciphers on Chain B for round 1:")
for idx, c in enumerate(ciphers):
    poster, roundId, cid, root, ts = c
    try:
        root_hex = root.hex()
    except:
        root_hex = str(root)
    print(f"{idx}: poster={poster}, roundId={roundId}, cid={cid}, root={root_hex}, ts={ts}")
