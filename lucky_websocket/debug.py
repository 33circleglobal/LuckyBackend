# quick debug script
from web3 import Web3
from contract.client import contract_client
from config import POOL_ID_BYTES

result = contract_client.contract.functions.isPoolOpen(POOL_ID_BYTES).call()
print("isPoolOpen:", result)
