import json
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
with open('python/abi/DKGRegistry.json','r',encoding='utf-8') as f:
    art = json.load(f)
abi = art.get('abi', art)
dkg = w3.eth.contract(address=w3.to_checksum_address('0x5FbDB2315678afecb367f032d93F642f64180aa3'), abi=abi)
try:
    last = dkg.functions.lastRound().call()
except Exception:
    last = 0
print(last + 1)
