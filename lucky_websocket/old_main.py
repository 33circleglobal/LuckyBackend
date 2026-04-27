import asyncio
import json
import time
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Tuple
from web3 import Web3
from eth_account import Account
import os
from decouple import config

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

RPC_URL = config("RPC_URL", "http://127.0.0.1:8545")
print(RPC_URL)
GAME_MANAGER_PRIVATE_KEY = config(
    "GAME_MANAGER_PRIVATE_KEY",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
)
CONTRACT_ADDRESS = config(
    "CONTRACT_ADDRESS", "0x5fbdb2315678afecb367f032d93f642f64180aa3"
)
PLAYING_CAPACITY = 100

POOL_ID_BYTES = Web3.to_bytes(text="btc-battle-pool-1").ljust(32, b"\x00")
POOL_ID_HEX = "0x" + POOL_ID_BYTES.hex()

# ──────────────────────────────────────────────
# ABI
# ──────────────────────────────────────────────

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_owner", "type": "address"},
            {"internalType": "address", "name": "_gameManager", "type": "address"},
            {
                "internalType": "address",
                "name": "_treasuryAffiliateWallet",
                "type": "address",
            },
            {
                "internalType": "address",
                "name": "_treasuryJackpotWallet",
                "type": "address",
            },
            {"internalType": "address", "name": "_treasuryWallet", "type": "address"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {"inputs": [], "name": "CallerNotAuthorized", "type": "error"},
    {"inputs": [], "name": "EtherTransferFailed", "type": "error"},
    {"inputs": [], "name": "GameNotRunning", "type": "error"},
    {"inputs": [], "name": "InvalidFeePercentage", "type": "error"},
    {"inputs": [], "name": "MaxBetAmountError", "type": "error"},
    {"inputs": [], "name": "MinBetAmountError", "type": "error"},
    {"inputs": [], "name": "PendingDistributions", "type": "error"},
    {"inputs": [], "name": "PoolIsFull", "type": "error"},
    {"inputs": [], "name": "RoundHasEnded", "type": "error"},
    {"inputs": [], "name": "RoundNotExists", "type": "error"},
    {"inputs": [], "name": "RoundNotOpen", "type": "error"},
    {"inputs": [], "name": "RoundNotStarted", "type": "error"},
    {"inputs": [], "name": "SenderNotEOAOrAllowed", "type": "error"},
    {"inputs": [], "name": "ZeroAddressNotAllowed", "type": "error"},
    {
        "inputs": [
            {"internalType": "bytes", "name": "poolId", "type": "bytes"},
            {"internalType": "uint256", "name": "minPlayWorth", "type": "uint256"},
            {"internalType": "uint256", "name": "maxPlayWorth", "type": "uint256"},
            {"internalType": "uint256", "name": "playingCapacity", "type": "uint256"},
            {"internalType": "uint256", "name": "roundStartTime", "type": "uint256"},
            {"internalType": "uint256", "name": "roundEndTime", "type": "uint256"},
            {"internalType": "uint32", "name": "roundId", "type": "uint32"},
        ],
        "name": "createGamePipeline",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "poolId", "type": "bytes"},
            {"internalType": "int32", "name": "startPrice", "type": "int32"},
        ],
        "name": "startRound",
        "outputs": [
            {"internalType": "bool", "name": "success", "type": "bool"},
            {"internalType": "int32", "name": "actualStartPrice", "type": "int32"},
            {"internalType": "uint256", "name": "roundNumber", "type": "uint256"},
            {"internalType": "uint256", "name": "totalUpBets", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDownBets", "type": "uint256"},
            {"internalType": "uint256", "name": "totalUpWager", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDownWager", "type": "uint256"},
            {
                "internalType": "address[]",
                "name": "upParticipants",
                "type": "address[]",
            },
            {"internalType": "uint256[]", "name": "upAmounts", "type": "uint256[]"},
            {
                "internalType": "address[]",
                "name": "downParticipants",
                "type": "address[]",
            },
            {"internalType": "uint256[]", "name": "downAmounts", "type": "uint256[]"},
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes", "name": "poolId", "type": "bytes"},
            {"internalType": "int32", "name": "endPrice", "type": "int32"},
            {"internalType": "uint256", "name": "playingCapacity", "type": "uint256"},
        ],
        "name": "endRound",
        "outputs": [
            {"internalType": "bool", "name": "success", "type": "bool"},
            {"internalType": "int32", "name": "actualEndPrice", "type": "int32"},
            {"internalType": "uint256", "name": "roundNumber", "type": "uint256"},
            {"internalType": "string", "name": "priceMovement", "type": "string"},
            {"internalType": "uint256", "name": "totalWinners", "type": "uint256"},
            {"internalType": "uint256", "name": "totalLosers", "type": "uint256"},
            {
                "internalType": "uint256",
                "name": "distributionsProcessed",
                "type": "uint256",
            },
            {
                "internalType": "bool",
                "name": "allDistributionsComplete",
                "type": "bool",
            },
            {
                "internalType": "address[]",
                "name": "winnerAddresses",
                "type": "address[]",
            },
            {
                "internalType": "uint256[]",
                "name": "winnerOriginalAmounts",
                "type": "uint256[]",
            },
            {
                "internalType": "uint256[]",
                "name": "winnerTotalPayouts",
                "type": "uint256[]",
            },
            {
                "internalType": "uint256[]",
                "name": "winningAmounts",
                "type": "uint256[]",
            },
        ],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "poolId", "type": "bytes"}],
        "name": "clearGamePipeline",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes", "name": "poolId", "type": "bytes"}],
        "name": "isPoolOpen",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ──────────────────────────────────────────────
# WEB3 SETUP
# ──────────────────────────────────────────────

w3 = Web3(Web3.HTTPProvider(RPC_URL))
game_manager_account = Account.from_key(GAME_MANAGER_PRIVATE_KEY)
contract = None


def get_contract():
    global contract
    if contract is None:
        if not CONTRACT_ADDRESS:
            raise RuntimeError("CONTRACT_ADDRESS env var not set")
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI,
        )
    return contract


def price_to_int32(price: float) -> int:
    return int(price)


def send_tx(fn):
    nonce = w3.eth.get_transaction_count(game_manager_account.address)
    tx = fn.build_transaction(
        {
            "from": game_manager_account.address,
            "nonce": nonce,
            "gas": 500_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = game_manager_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
    return receipt


def call_fn(fn):
    """Simulate a call (no state change) to read return values."""
    return fn.call({"from": game_manager_account.address})


# ──────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────

clients_ws1: List[WebSocket] = []
clients_ws2: List[WebSocket] = []
price_buffer: List[Tuple[int, float]] = []
MAX_BUFFER_SIZE = 1200

latest_price_data = {"price": None, "timestamp": None}

current_game = {
    "cycle_start": None,
    "start_price": None,
    "end_price": None,
    "result": None,
    "pool_id": POOL_ID_HEX,
}

round_id_counter = 0


# ──────────────────────────────────────────────
# CONTRACT HELPERS
# ──────────────────────────────────────────────


async def contract_create_pipeline(round_id: int, start_time: int, end_time: int):
    try:
        c = get_contract()
        fn = c.functions.createGamePipeline(
            POOL_ID_BYTES,
            Web3.to_wei(0.001, "ether"),
            Web3.to_wei(1, "ether"),
            PLAYING_CAPACITY,
            start_time,
            end_time,
            round_id,
        )
        receipt = await asyncio.get_event_loop().run_in_executor(None, send_tx, fn)
        print(
            f"[CONTRACT] Pipeline created | round={round_id} | block={receipt['blockNumber']}"
        )
        return True
    except Exception as e:
        print(f"[CONTRACT ERROR] createGamePipeline: {e}")
        return False


async def contract_start_round(price: float):
    try:
        c = get_contract()
        int_price = price_to_int32(price)
        fn = c.functions.startRound(POOL_ID_BYTES, int_price)

        # Simulate first to capture return values before state changes
        call_result = await asyncio.get_event_loop().run_in_executor(None, call_fn, fn)

        # Now send the real transaction
        receipt = await asyncio.get_event_loop().run_in_executor(None, send_tx, fn)

        print(f"[CONTRACT] startRound return values:")
        print(f"  success:           {call_result[0]}")
        print(f"  actualStartPrice:  {call_result[1]}")
        print(f"  roundNumber:       {call_result[2]}")
        print(f"  totalUpBets:       {call_result[3]}")
        print(f"  totalDownBets:     {call_result[4]}")
        print(f"  totalUpWager:      {Web3.from_wei(call_result[5], 'ether')} ETH")
        print(f"  totalDownWager:    {Web3.from_wei(call_result[6], 'ether')} ETH")
        print(f"  upParticipants:    {call_result[7]}")
        print(
            f"  upAmounts:         {[Web3.from_wei(a, 'ether') for a in call_result[8]]}"
        )
        print(f"  downParticipants:  {call_result[9]}")
        print(
            f"  downAmounts:       {[Web3.from_wei(a, 'ether') for a in call_result[10]]}"
        )
        print(f"  block={receipt['blockNumber']}")

        return call_result
    except Exception as e:
        print(f"[CONTRACT ERROR] startRound: {e}")
        return None


async def contract_end_round(price: float):
    try:
        c = get_contract()
        int_price = price_to_int32(price)
        fn = c.functions.endRound(POOL_ID_BYTES, int_price, PLAYING_CAPACITY)

        # Simulate first to capture return values before state changes
        call_result = await asyncio.get_event_loop().run_in_executor(None, call_fn, fn)

        # Now send the real transaction
        receipt = await asyncio.get_event_loop().run_in_executor(None, send_tx, fn)

        print(f"[CONTRACT] endRound return values:")
        print(f"  success:                  {call_result[0]}")
        print(f"  actualEndPrice:           {call_result[1]}")
        print(f"  roundNumber:              {call_result[2]}")
        print(f"  priceMovement:            {call_result[3]}")
        print(f"  totalWinners:             {call_result[4]}")
        print(f"  totalLosers:              {call_result[5]}")
        print(f"  distributionsProcessed:   {call_result[6]}")
        print(f"  allDistributionsComplete: {call_result[7]}")
        print(f"  winnerAddresses:          {call_result[8]}")
        print(
            f"  winnerOriginalAmounts:    {[Web3.from_wei(a, 'ether') for a in call_result[9]]}"
        )
        print(
            f"  winnerTotalPayouts:       {[Web3.from_wei(a, 'ether') for a in call_result[10]]}"
        )
        print(
            f"  winningAmounts:           {[Web3.from_wei(a, 'ether') for a in call_result[11]]}"
        )
        print(f"  block={receipt['blockNumber']}")

        return call_result
    except Exception as e:
        print(f"[CONTRACT ERROR] endRound: {e}")
        return None


async def contract_clear_pipeline():
    try:
        c = get_contract()
        fn = c.functions.clearGamePipeline(POOL_ID_BYTES)
        receipt = await asyncio.get_event_loop().run_in_executor(None, send_tx, fn)
        print(f"[CONTRACT] clearGamePipeline | block={receipt['blockNumber']}")
        return True
    except Exception as e:
        print(f"[CONTRACT ERROR] clearGamePipeline: {e}")
        return False


# ──────────────────────────────────────────────
# BINANCE LISTENER
# ──────────────────────────────────────────────


async def binance_listener():
    url = "wss://fstream.binance.com/ws/btcusdt@trade"
    reconnect_delay = 1
    max_reconnect_delay = 60

    while True:
        try:
            print(f"Connecting to Binance WebSocket: {url}")
            async with websockets.connect(
                url, ping_interval=180, ping_timeout=600, close_timeout=10
            ) as ws:
                print("Connected to Binance WebSocket")
                reconnect_delay = 1
                connection_start = time.time()
                async for message in ws:
                    try:
                        if time.time() - connection_start > 23.5 * 3600:
                            print("Approaching 24-hour limit, reconnecting...")
                            break
                        data = json.loads(message)
                        latest_price_data["price"] = float(data["p"])
                        latest_price_data["timestamp"] = int(data["T"])
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        continue
        except Exception as e:
            print(f"WebSocket error: {e}")

        print(f"Reconnecting in {reconnect_delay} seconds...")
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


# ──────────────────────────────────────────────
# PRICE BROADCASTER
# ──────────────────────────────────────────────


async def price_broadcaster():
    while True:
        start_time = time.time()
        if (
            latest_price_data["price"] is not None
            and latest_price_data["timestamp"] is not None
        ):
            current_price = latest_price_data["price"]
            current_timestamp = int(time.time() * 1000)

            price_buffer.append((current_timestamp, current_price))
            if len(price_buffer) > MAX_BUFFER_SIZE:
                price_buffer.pop(0)

            await broadcast(
                clients_ws1,
                json.dumps(
                    {
                        "price": current_price,
                        "timestamp": current_timestamp,
                        "pool_id": current_game["pool_id"],
                    }
                ),
            )

        elapsed = (time.time() - start_time) * 1000
        sleep_time = max(0, (75 - elapsed) / 1000)
        await asyncio.sleep(sleep_time)


# ──────────────────────────────────────────────
# BROADCAST HELPER
# ──────────────────────────────────────────────


async def broadcast(clients: List[WebSocket], message: str):
    disconnected = []
    for client in clients:
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)
    for client in disconnected:
        if client in clients:
            clients.remove(client)


def get_price_at(target_ts: int) -> Optional[float]:
    if not price_buffer:
        return None
    return min(price_buffer, key=lambda x: abs(x[0] - target_ts))[1]


# ──────────────────────────────────────────────
# WEBSOCKET ENDPOINTS
# ──────────────────────────────────────────────


@app.websocket("/ws1")
async def websocket_stream_binance(websocket: WebSocket):
    await websocket.accept()
    clients_ws1.append(websocket)

    history = [
        {"price": price, "timestamp": ts, "pool_id": current_game["pool_id"]}
        for ts, price in price_buffer
    ]
    await websocket.send_text(json.dumps({"type": "history", "data": history}))

    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        if websocket in clients_ws1:
            clients_ws1.remove(websocket)


@app.websocket("/ws2")
async def websocket_game_logic(websocket: WebSocket):
    await websocket.accept()
    clients_ws2.append(websocket)

    if current_game["start_price"] is not None:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "start_price",
                    "price": current_game["start_price"],
                    "pool_id": current_game["pool_id"],
                }
            )
        )
    if current_game["end_price"] is not None:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "end_price",
                    "price": current_game["end_price"],
                    "pool_id": current_game["pool_id"],
                }
            )
        )
    if current_game["result"] is not None:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "result",
                    "result": current_game["result"],
                    "start_price": current_game["start_price"],
                    "end_price": current_game["end_price"],
                    "pool_id": current_game["pool_id"],
                }
            )
        )

    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        if websocket in clients_ws2:
            clients_ws2.remove(websocket)


# ──────────────────────────────────────────────
# GAME LOOP
# ──────────────────────────────────────────────


async def game_loop():
    global round_id_counter
    cycle_duration = 60_000  # ms

    print("[GAME] Waiting for first price from Binance...")
    while latest_price_data["price"] is None:
        await asyncio.sleep(0.5)
    print("[GAME] Price received, starting game loop")

    while True:
        now_ms = int(time.time() * 1000)
        cycle_start = now_ms - (now_ms % cycle_duration)

        t_start = cycle_start + 40_000
        t_end = cycle_start + 55_000
        t_next = cycle_start + cycle_duration

        round_id_counter += 1
        current_round_id = round_id_counter

        current_game.update(
            {
                "cycle_start": cycle_start,
                "start_price": None,
                "end_price": None,
                "result": None,
                "pool_id": POOL_ID_HEX,
            }
        )

        # ── 0s: Create pipeline ──
        now_s = int(time.time())
        pipeline_ok = await contract_create_pipeline(
            round_id=current_round_id,
            start_time=now_s,
            end_time=now_s + 39,
        )
        if not pipeline_ok:
            print(
                f"[GAME] Pipeline creation failed for round {current_round_id}, skipping cycle"
            )
            await asyncio.sleep(max((t_next - int(time.time() * 1000)) / 1000, 0))
            continue

        # ── Wait until 40s mark ──
        await asyncio.sleep(max((t_start - int(time.time() * 1000)) / 1000, 0))

        start_price = get_price_at(t_start)
        current_game["start_price"] = start_price

        await broadcast(
            clients_ws2,
            json.dumps(
                {
                    "type": "start_price",
                    "price": start_price,
                    "pool_id": current_game["pool_id"],
                }
            ),
        )

        if start_price is not None:
            await contract_start_round(start_price)
        else:
            print("[GAME] No start price, skipping startRound")

        # ── Wait until 55s mark ──
        await asyncio.sleep(max((t_end - int(time.time() * 1000)) / 1000, 0))

        end_price = get_price_at(t_end)
        current_game["end_price"] = end_price

        await broadcast(
            clients_ws2,
            json.dumps(
                {
                    "type": "end_price",
                    "price": end_price,
                    "pool_id": current_game["pool_id"],
                }
            ),
        )

        if start_price is not None and end_price is not None:
            await contract_end_round(end_price)
        else:
            print("[GAME] Missing prices, skipping endRound")

        result = (
            "no_result"
            if start_price is None or end_price is None
            else (
                "up"
                if end_price > start_price
                else "down" if end_price < start_price else "same"
            )
        )
        current_game["result"] = result

        await broadcast(
            clients_ws2,
            json.dumps(
                {
                    "type": "result",
                    "result": result,
                    "start_price": start_price,
                    "end_price": end_price,
                    "pool_id": current_game["pool_id"],
                }
            ),
        )

        # ── Sleep to next cycle then clear ──
        await asyncio.sleep(max((t_next - int(time.time() * 1000)) / 1000, 0))
        await contract_clear_pipeline()


# ──────────────────────────────────────────────
# STARTUP
# ──────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    if not CONTRACT_ADDRESS:
        print("[WARN] CONTRACT_ADDRESS not set — contract calls will fail.")
    asyncio.create_task(binance_listener())
    asyncio.create_task(price_broadcaster())
    asyncio.create_task(game_loop())
