import json
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8546"))
with open("python/abi/DKGRegistry.json","r",encoding="utf-8") as f:
    art = json.load(f)
abi = art.get("abi", art)
dkg_b = "0x8464135c8F25Da09e49BC8782676a84730C318bC"
c = w3.eth.contract(address=w3.to_checksum_address(dkg_b), abi=abi)
info = c.functions.getRoundInfo(1).call()
# print nicely: initiator, roundId, root(hex), cid, timestamp
initiator, roundId, root, cid, ts = info
try:
    root_hex = root.hex()
except:
    root_hex = str(root)
print("Chain B getRoundInfo(1):")
print("  initiator:", initiator)
print("  roundId:  ", roundId)
print("  merkleRoot:", root_hex)
print("  metadataCID:", cid)
print("  timestamp:", ts)
