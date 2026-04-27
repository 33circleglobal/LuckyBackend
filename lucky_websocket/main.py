import asyncio
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import POOL_ID_HEX
from game.loop import game_loop
from game.state import game_state
from price.binance import binance_listener, price_broadcaster
from price.buffer import price_buffer
from ws.manager import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws1")
async def ws_price_stream(websocket: WebSocket):
    await websocket.accept()
    ws_manager.add_price_client(websocket)

    # Send history on connect
    history = [
        {"price": price, "timestamp": ts, "pool_id": POOL_ID_HEX}
        for ts, price in price_buffer.snapshot()
    ]
    await ws_manager.send_to(websocket, {"type": "history", "data": history})

    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        ws_manager.remove_price_client(websocket)


@app.websocket("/ws2")
async def ws_game_events(websocket: WebSocket):
    await websocket.accept()
    ws_manager.add_game_client(websocket)

    # Send current round state on connect
    for msg in game_state.to_ws2_snapshot():
        await ws_manager.send_to(websocket, msg)

    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        ws_manager.remove_game_client(websocket)


@app.on_event("startup")
async def startup():
    asyncio.create_task(binance_listener())
    asyncio.create_task(price_broadcaster())
    asyncio.create_task(game_loop())
