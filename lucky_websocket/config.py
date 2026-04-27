from decouple import config
from web3 import Web3

RPC_URL = config("RPC_URL", "http://127.0.0.1:8545")
GAME_MANAGER_PRIVATE_KEY = config(
    "GAME_MANAGER_PRIVATE_KEY",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
)
CONTRACT_ADDRESS = config(
    "CONTRACT_ADDRESS", "0x5fbdb2315678afecb367f032d93f642f64180aa3"
)
PLAYING_CAPACITY = 100
CYCLE_DURATION_MS = 60_000
PRICE_BROADCAST_INTERVAL_MS = 75
MAX_PRICE_BUFFER = 1200
BINANCE_WS_URL = "wss://fstream.binance.com/ws/btcusdt@trade"

DJANGO_API_URL = config("DJANGO_API_URL", "http://127.0.0.1:8000/api/games/")
DJANGO_API_SECRET = config(
    "DJANGO_API_SECRET", "(uqd3o&-^vhrxzjvsde7*8r-_@b!kvf6sucb$mlp5pb(w-fhgc"
)

POOL_ID_HEX = config("POOL_ID_HEX", "0xDEADBEEF")
POOL_ID_BYTES = bytes.fromhex(POOL_ID_HEX.removeprefix("0x"))
