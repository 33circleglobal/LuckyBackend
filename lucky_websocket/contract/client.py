import asyncio
from web3 import Web3
from eth_account import Account
from config import RPC_URL, GAME_MANAGER_PRIVATE_KEY, CONTRACT_ADDRESS
from contract.abi import CONTRACT_ABI


class ContractClient:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.account = Account.from_key(GAME_MANAGER_PRIVATE_KEY)
        self._contract = None

    @property
    def contract(self):
        if self._contract is None:
            self._contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=CONTRACT_ABI,
            )
        return self._contract

    def _send_tx(self, fn):
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = fn.build_transaction(
            {
                "from": self.account.address,
                "nonce": nonce,
                "gas": 500_000,
                "gasPrice": self.w3.eth.gas_price,
            }
        )
        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

    def _call_fn(self, fn):
        return fn.call({"from": self.account.address})

    async def send(self, fn):
        return await asyncio.get_event_loop().run_in_executor(None, self._send_tx, fn)

    async def call(self, fn):
        return await asyncio.get_event_loop().run_in_executor(None, self._call_fn, fn)


# Singleton — imported everywhere
contract_client = ContractClient()
