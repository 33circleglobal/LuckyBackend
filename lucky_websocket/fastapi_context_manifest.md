# Project Context Manifest — FastAPI Service
# BTC Battle — Price Feed & Game Orchestration
# Version: 1.0 | Last Updated: 2026-04-26

---

## 1. SERVICE OVERVIEW

**Service name:** BTC Battle FastAPI  
**Role:** Game orchestrator — fetches live BTC price, drives 60-second round cycles,
interacts with the smart contract, broadcasts events to frontend clients via WebSocket,
and notifies Django after each round via HMAC-signed HTTP POST.  
**Language:** Python 3.11+  
**Framework:** FastAPI + asyncio  
**Key dependencies:** `web3`, `eth-account`, `websockets`, `aiohttp`, `fastapi`, `uvicorn`

---

## 2. FOLDER STRUCTURE

```
fastapi_app/
├── main.py                  # App entry point, WS endpoints, startup tasks
├── config.py                # All env vars + constants (single source of truth)
├── contract/
│   ├── __init__.py
│   ├── abi.py               # Full Solidity contract ABI
│   ├── client.py            # ContractClient singleton (web3 + account)
│   └── helpers.py           # create_pipeline, start_round, end_round, clear_pipeline
├── game/
│   ├── __init__.py
│   ├── loop.py              # 60s cycle orchestrator (core game logic)
│   └── state.py             # GameState singleton (current round snapshot)
├── ws/
│   ├── __init__.py
│   └── manager.py           # WebSocketManager singleton (ws1 + ws2 client lists)
├── price/
│   ├── __init__.py
│   ├── binance.py           # Binance WS listener + 75ms price broadcaster
│   └── buffer.py            # PriceBuffer singleton (ring buffer, get_at)
└── django_client/
    ├── __init__.py
    └── poster.py            # post_round_started(), post_round_ended() with HMAC signing
```

---

## 3. config.py

**Purpose:** Single source of truth for all configuration. Every other module imports
from here — never use `os.getenv` anywhere else.

```python
import os
from web3 import Web3

RPC_URL                  = os.getenv("RPC_URL", "http://127.0.0.1:8545")
GAME_MANAGER_PRIVATE_KEY = os.getenv("GAME_MANAGER_PRIVATE_KEY", "0x59c6995e...")
CONTRACT_ADDRESS         = os.getenv("CONTRACT_ADDRESS", "0x5fbdb231...")
PLAYING_CAPACITY         = 100
CYCLE_DURATION_MS        = 60_000
PRICE_BROADCAST_INTERVAL_MS = 75
MAX_PRICE_BUFFER         = 1200
BINANCE_WS_URL           = "wss://fstream.binance.com/ws/btcusdt@trade"
DJANGO_API_URL           = os.getenv("DJANGO_API_URL", "http://127.0.0.1:8000/api/internal/")
DJANGO_API_SECRET        = os.getenv("DJANGO_API_SECRET", "")

POOL_ID_BYTES = Web3.to_bytes(text="btc-battle-pool-1").ljust(32, b"\x00")
POOL_ID_HEX   = "0x" + POOL_ID_BYTES.hex()
```

**Environment variables (production .env):**
```env
RPC_URL=https://your-rpc-node
GAME_MANAGER_PRIVATE_KEY=0x...
CONTRACT_ADDRESS=0x...
DJANGO_API_URL=http://django-service/api/internal/
DJANGO_API_SECRET=<openssl rand -hex 32>
```

---

## 4. contract/abi.py

**Purpose:** Holds the complete Solidity ABI. No logic — data only.

**Functions defined in ABI:**

| Function              | Type       | Inputs                                                | Outputs                                        |
|-----------------------|------------|-------------------------------------------------------|------------------------------------------------|
| `createGamePipeline`  | nonpayable | poolId, minPlayWorth, maxPlayWorth, capacity, startTime, endTime, roundId | none |
| `startRound`          | nonpayable | poolId, startPrice (int32)                            | success, actualStartPrice, roundNumber, totalUpBets, totalDownBets, totalUpWager, totalDownWager, upParticipants[], upAmounts[], downParticipants[], downAmounts[] |
| `endRound`            | nonpayable | poolId, endPrice (int32), playingCapacity             | success, actualEndPrice, roundNumber, priceMovement, totalWinners, totalLosers, distributionsProcessed, allDistributionsComplete, winnerAddresses[], winnerOriginalAmounts[], winnerTotalPayouts[], winningAmounts[] |
| `clearGamePipeline`   | nonpayable | poolId                                                | none                                           |
| `isPoolOpen`          | view       | poolId                                                | bool                                           |

**Custom errors defined:** `CallerNotAuthorized`, `EtherTransferFailed`, `GameNotRunning`,
`InvalidFeePercentage`, `MaxBetAmountError`, `MinBetAmountError`, `PendingDistributions`,
`PoolIsFull`, `RoundHasEnded`, `RoundNotExists`, `RoundNotOpen`, `RoundNotStarted`,
`SenderNotEOAOrAllowed`, `ZeroAddressNotAllowed`

---

## 5. contract/client.py

**Purpose:** Web3 connection + account singleton. Provides `send()` and `call()` async
wrappers that run blocking web3 calls in an executor.

**Class:** `ContractClient`  
**Singleton:** `contract_client = ContractClient()` — import this, never reinstantiate.

```python
# Key methods
async def send(self, fn) -> receipt     # builds, signs, sends tx, waits for receipt
async def call(self, fn) -> result      # simulates call, returns decoded values
```

**Critical rule:** `call()` is always run before `send()` for functions that return values
(`startRound`, `endRound`). This is because EVM transactions do not return values to the
caller — only `eth_call` simulations do.

---

## 6. contract/helpers.py

**Purpose:** One async function per contract interaction. Returns structured dicts or
`None`/`bool` on failure. All logging lives here.

### `create_pipeline(round_id, start_time, end_time) -> bool`
- Calls `createGamePipeline` with fixed min=0.001 ETH, max=1 ETH, capacity=PLAYING_CAPACITY
- Returns `True` on success, `False` on exception
- On failure: game loop skips this cycle entirely

### `start_round(price: float) -> dict | None`
Returns:
```python
{
    "success": bool,
    "actual_start_price": int,
    "round_number": int,
    "total_up_bets": int,
    "total_down_bets": int,
    "total_up_wager_wei": int,
    "total_down_wager_wei": int,
    "up_participants": list[str],
    "up_amounts": list[int],
    "down_participants": list[str],
    "down_amounts": list[int],
    "block": int,
}
```

### `end_round(price: float) -> dict | None`
Returns:
```python
{
    "success": bool,
    "actual_end_price": int,
    "round_number": int,
    "price_movement": str,           # "UP", "DOWN", "SAME"
    "total_winners": int,
    "total_losers": int,
    "distributions_processed": int,
    "all_distributions_complete": bool,
    "winner_addresses": list[str],
    "winner_original_amounts_wei": list[int],
    "winner_total_payouts_wei": list[int],
    "winning_amounts_wei": list[int],
    "block": int,
}
```

### `clear_pipeline() -> bool`
- Simple fire-and-forget at end of cycle
- Returns `True` on success

### Price conversion
```python
def price_to_int32(price: float) -> int:
    return int(price)   # BTC price truncated to integer for contract
```

---

## 7. price/buffer.py

**Purpose:** Thread-safe in-memory ring buffer for BTC price ticks.

**Class:** `PriceBuffer`  
**Singleton:** `price_buffer = PriceBuffer()`

```python
price_buffer.push(timestamp_ms: int, price: float)
price_buffer.get_at(target_ts: int) -> float | None   # nearest price to target timestamp
price_buffer.snapshot() -> list[tuple[int, float]]    # full buffer copy for ws history
price_buffer.latest_price -> float | None             # last known price
```

**Buffer size:** 1200 entries (MAX_PRICE_BUFFER) = ~90 seconds at 75ms intervals  
**Eviction:** oldest entry dropped when full (FIFO)  
**get_at logic:** finds entry with minimum `abs(ts - target_ts)` — closest match, not interpolated

---

## 8. price/binance.py

**Purpose:** Two long-running async tasks — one listens to Binance, one broadcasts.

### `binance_listener()`
- Connects to `wss://fstream.binance.com/ws/btcusdt@trade`
- Parses `{"p": price, "T": timestamp}` from trade stream
- Calls `price_buffer.push()` on every message
- Reconnects with exponential backoff (1s → 60s max)
- Reconnects after 23.5 hours to avoid Binance 24h limit

### `price_broadcaster()`
- Runs every 75ms
- Reads `price_buffer.latest_price`
- Broadcasts to all ws1 clients via `ws_manager.broadcast_price()`
- Message: `{"price": float, "timestamp": int_ms, "pool_id": str}`
- Skips broadcast if no price available yet

---

## 9. ws/manager.py

**Purpose:** Manages two lists of connected WebSocket clients. Handles dead connections silently.

**Class:** `WebSocketManager`  
**Singleton:** `ws_manager = WebSocketManager()`

```python
# Client registration
ws_manager.add_price_client(ws)      # ws1 connections
ws_manager.remove_price_client(ws)
ws_manager.add_game_client(ws)       # ws2 connections
ws_manager.remove_game_client(ws)

# Broadcasting
await ws_manager.broadcast_price(payload: dict)   # → all ws1 clients
await ws_manager.broadcast_game(payload: dict)    # → all ws2 clients
await ws_manager.send_to(ws, payload: dict)       # → single client (used on connect)
```

**Dead client handling:** on send failure, client is collected and removed from list.
No exception is raised — silent cleanup.

---

## 10. game/state.py

**Purpose:** Holds the current round's in-memory state. Sent as a snapshot to new ws2
connections so they immediately get current round context.

**Class:** `GameState`  
**Singleton:** `game_state = GameState()`

```python
game_state.pool_id      # str  — POOL_ID_HEX, NEVER reset to None
game_state.cycle_start  # int | None
game_state.start_price  # float | None
game_state.end_price    # float | None
game_state.result       # "up" | "down" | "same" | "no_result" | None

game_state.reset_cycle(cycle_start: int)    # called at start of each cycle
game_state.set_start(price: float)          # sets start_price
game_state.set_end(price: float)            # sets end_price + computes result
game_state.to_ws2_snapshot() -> list[dict]  # messages to send on fresh ws2 connect
```

**Result computation (in set_end):**
```
end > start  → "up"
end < start  → "down"
end == start → "same"
either None  → "no_result"
```

**Critical rule:** `pool_id` is set once at startup and never cleared. Every ws message
always carries a valid `pool_id`, even between cycles.

---

## 11. game/loop.py

**Purpose:** The core game orchestrator. One infinite loop, one 60-second cycle.

**Singleton state:** `round_id_counter` (module-level int, increments each cycle)

### Cycle Timeline

```
t=0s   reset_cycle() → createGamePipeline()
          └── on failure: log + skip to next cycle

t=40s  get price from buffer at t_start timestamp
          → game_state.set_start(price)
          → broadcast ws2: {"type": "start_price", ...}
          → contract.start_round(price) → returns start_data dict
          → django_client.post_round_started(round_id, start_data)

t=55s  get price from buffer at t_end timestamp
          → game_state.set_end(price)
          → broadcast ws2: {"type": "end_price", ...}
          → contract.end_round(price) → returns end_data dict
          → django_client.post_round_ended(end_data)
          → broadcast ws2: {"type": "result", ...}

t=60s  contract.clear_pipeline()
          → next cycle begins immediately
```

### Timing helper
```python
def _ms() -> int:
    return int(time.time() * 1000)

async def _sleep_until(target_ms: int):
    delay = (target_ms - _ms()) / 1000
    if delay > 0:
        await asyncio.sleep(delay)
```

### Cycle alignment
```python
now_ms      = _ms()
cycle_start = now_ms - (now_ms % CYCLE_DURATION_MS)  # snaps to minute boundary
t_start     = cycle_start + 40_000
t_end       = cycle_start + 55_000
t_next      = cycle_start + CYCLE_DURATION_MS
```

### Guard conditions
- `start_price is None` → skip `startRound`, log warning
- `start_price or end_price is None` → skip `endRound`, log warning
- `start_data is None` → skip Django POST for round_started
- `end_data is None` → skip Django POST for round_ended
- Pipeline creation failure → skip entire cycle, sleep to next

---

## 12. django_client/poster.py

**Purpose:** Signs and POSTs round data to Django after each contract interaction.

### Security
- Every POST body is HMAC-SHA256 signed with `DJANGO_API_SECRET`
- Signature sent in `X-Signature` header
- Django verifies this header before processing

```python
def _sign(payload: str) -> str:
    return hmac.new(
        DJANGO_API_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
```

### `post_round_started(round_id, start_data)`
POSTs to `/api/internal/round-started/`:
```json
{
    "type": "round_started",
    "pool_id": "0x...",
    "round_id": 42,
    "round_number": 13,
    "actual_start_price": 77643,
    "total_up_bets": 5,
    "total_down_bets": 3,
    "total_up_wager_wei": "5000000000000000",
    "total_down_wager_wei": "3000000000000000",
    "up_participants": ["0x...", "0x..."],
    "up_amounts": [1000000000000000, ...],
    "down_participants": ["0x..."],
    "down_amounts": [500000000000000],
    "block": 103483236
}
```

### `post_round_ended(end_data)`
POSTs to `/api/internal/round-ended/`:
```json
{
    "type": "round_ended",
    "pool_id": "0x...",
    "round_number": 13,
    "actual_end_price": 77667,
    "price_movement": "UP",
    "total_winners": 5,
    "total_losers": 3,
    "distributions_processed": 5,
    "all_distributions_complete": true,
    "winner_addresses": ["0x...", "0x..."],
    "winner_original_amounts_wei": ["1000000000000000", ...],
    "winner_total_payouts_wei": ["1800000000000000", ...],
    "winning_amounts_wei": ["800000000000000", ...],
    "block": 103483267
}
```

**Failure handling:** all POST failures are logged and swallowed — game cycle is never
blocked by Django being down. Fire-and-forget pattern.  
**Timeout:** 10 seconds (`aiohttp.ClientTimeout(total=10)`)

---

## 13. main.py

**Purpose:** FastAPI app definition, WebSocket endpoint handlers, startup task launcher.

### WebSocket Endpoints

#### `/ws1` — Price Stream
```
ON CONNECT:
  1. Accept connection
  2. Add to ws_manager price clients
  3. Send history snapshot: {"type": "history", "data": [{price, timestamp, pool_id}, ...]}

WHILE CONNECTED:
  Receives 75ms price broadcasts from price_broadcaster()

ON DISCONNECT:
  Remove from ws_manager price clients
```

#### `/ws2` — Game Events
```
ON CONNECT:
  1. Accept connection
  2. Add to ws_manager game clients
  3. Send current round state snapshot (0–3 messages depending on cycle position):
     - start_price message (if round has started)
     - end_price message (if round has ended)
     - result message (if result is known)

WHILE CONNECTED:
  Receives game events from game_loop():
  - start_price at t=40s
  - end_price at t=55s
  - result at t=55s

ON DISCONNECT:
  Remove from ws_manager game clients
```

### Startup Tasks
```python
@app.on_event("startup")
async def startup():
    asyncio.create_task(binance_listener())    # price/binance.py
    asyncio.create_task(price_broadcaster())   # price/binance.py
    asyncio.create_task(game_loop())           # game/loop.py
```

### CORS
```python
allow_origins=["*"]   # tighten in production to frontend domain
```

---

## 14. WEBSOCKET MESSAGE REFERENCE

### ws1 — Price Stream (server → client)

**On connect (history):**
```json
{
    "type": "history",
    "data": [
        {"price": 77640.5, "timestamp": 1714123400000, "pool_id": "0x..."},
        {"price": 77641.2, "timestamp": 1714123400075, "pool_id": "0x..."}
    ]
}
```

**Every 75ms (tick):**
```json
{"price": 77643.5, "timestamp": 1714123456789, "pool_id": "0x..."}
```

### ws2 — Game Events (server → client)

```json
{"type": "start_price", "price": 77643, "pool_id": "0x..."}
{"type": "end_price",   "price": 77667, "pool_id": "0x..."}
{
    "type": "result",
    "result": "up",
    "start_price": 77643,
    "end_price": 77667,
    "pool_id": "0x..."
}
```

**result values:** `"up"` | `"down"` | `"same"` | `"no_result"`

---

## 15. SINGLETON MAP

| Singleton          | Module                   | Import as              |
|--------------------|--------------------------|------------------------|
| `contract_client`  | `contract/client.py`     | `from contract.client import contract_client` |
| `price_buffer`     | `price/buffer.py`        | `from price.buffer import price_buffer` |
| `game_state`       | `game/state.py`          | `from game.state import game_state` |
| `ws_manager`       | `ws/manager.py`          | `from ws.manager import ws_manager` |

**Rule:** Never reinstantiate these. Always import the module-level instance.

---

## 16. KEY DESIGN DECISIONS

1. **`call()` before `send()` for startRound and endRound**  
   EVM transactions do not return values to the caller over RPC. `eth_call` simulates
   the function and returns values without changing state. We call first to capture
   return values, then send the real transaction. Both use the same `fn` object.

2. **`pool_id` never set to None**  
   `game_state.pool_id` is set at module load to `POOL_ID_HEX` and never cleared.
   This ensures every ws1/ws2 message always carries a valid `pool_id`, even during
   the gap between cycles.

3. **Singletons via module-level instances**  
   All stateful objects are instantiated once at module level. Python's import system
   guarantees they are shared across all imports within the same process.

4. **`hmac.new()` not `hmac.HMAC()`**  
   Python's `hmac` module exposes `hmac.new(key, msg, digestmod)`. Do not use
   `hmac.HMAC()` — it is a class, not the intended public API.

5. **Price truncated to int32 for contract**  
   `price_to_int32(price) = int(price)` — BTC price in USD truncated. The contract
   stores and compares prices as `int32`. Decimals are discarded.

6. **Cycle alignment to wall-clock minute**  
   `cycle_start = now_ms - (now_ms % 60_000)` snaps each cycle to the current
   minute boundary. This means all nodes running this code stay in sync with
   the same minute boundaries without coordination.

7. **Fire-and-forget Django POST**  
   Game loop never awaits a confirmed Django response before continuing. A Django
   outage does not affect game operation. Missed POSTs are a data gap, not a crash.

8. **Dead WebSocket clients cleaned up lazily**  
   `ws_manager` collects failed clients during broadcast and removes them after
   the broadcast loop. No background cleanup task needed.

---

## 17. WHAT IS NOT IN THIS SERVICE

The following are handled by Django, not FastAPI:

- User/member records and VIP status
- Matrix earnings and binary tree placement
- Winning streak tracking and jackpot payouts
- Daily tournament win counting and finalization
- Team winning bonus distribution up referral chain
- Satoshi's Pick trigger and payout
- Top Producer scoring and period finalization
- Squad Showdown event management
- All persistent storage (FastAPI is stateless except in-memory buffer)
- Payment verification for VIP subscriptions

---

## 18. RUNNING THE SERVICE

```bash
# Install dependencies
pip install fastapi uvicorn websockets aiohttp web3 eth-account

# Run (development)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Run (production)
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1 --loop asyncio
```

**Important:** Use `--workers 1` only. The singletons (price_buffer, game_state,
ws_manager) are in-process memory. Multiple workers would have independent state,
causing split-brain on game state and duplicate contract transactions.

---

## 19. KNOWN GAPS / NEXT STEPS

- [ ] Graceful shutdown — drain ws clients before exit
- [ ] Retry queue for failed Django POSTs (currently fire-and-forget with no retry)
- [ ] CORS `allow_origins` locked to frontend domain in production
