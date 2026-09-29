from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from engine.reality.game import Law, RealityGame

app = FastAPI(title="REALITY")

INDEX = Path(__file__).resolve().parent.parent / "web" / "index.html"

games: dict[str, RealityGame] = {}
rooms: dict[str, dict[str, WebSocket]] = {}


def get_game(room_id: str) -> RealityGame:
    rooms.setdefault(room_id, {})
    return games.setdefault(room_id, RealityGame())


@app.get("/")
async def root():
    return FileResponse(INDEX)


async def broadcast(room_id: str) -> None:
    """Each observer gets their own view — readings are private until traded."""
    game = games[room_id]
    for pid, socket in list(rooms[room_id].items()):
        try:
            await socket.send_json({"type": "state", "state": game.state(viewer=pid)})
        except Exception:
            rooms[room_id].pop(pid, None)


@app.websocket("/ws/{room_id}")
async def play(websocket: WebSocket, room_id: str):
    await websocket.accept()
    game = get_game(room_id)

    seat = next((p for p in ("A", "B") if p not in rooms[room_id]), None)
    if seat is None:
        await websocket.send_json({"type": "error", "error": "room_full"})
        await websocket.close()
        return

    rooms[room_id][seat] = websocket
    await websocket.send_json({
        "type": "joined",
        "player_id": seat,
        "axis": "cos" if seat == "A" else "sin",
        "state": game.state(viewer=seat),
    })
    await broadcast(room_id)

    actions = {
        "observe": lambda msg: game.observe(seat),
        "advance": lambda msg: game.advance(seat),
        "trade": lambda msg: game.offer_trade(seat),
        "hypothesize": lambda msg: game.hypothesize(seat, Law(msg["law"])),
        "lock": lambda msg: game.lock(seat),
    }

    try:
        while True:
            message = await websocket.receive_json()
            handler = actions.get(message.get("action"))
            if handler is None:
                await websocket.send_json({"type": "error", "error": "unknown_action"})
                continue
            try:
                handler(message)
            except (KeyError, ValueError):
                await websocket.send_json({"type": "error", "error": "bad_action"})
                continue
            await broadcast(room_id)
    except Exception:
        # Starlette raises more than one disconnect type depending on version;
        # any failure here means this observer is gone.
        pass
    finally:
        # Must always run, or the seat stays occupied and the room locks up.
        rooms.get(room_id, {}).pop(seat, None)
        if not rooms.get(room_id):
            rooms.pop(room_id, None)
            games.pop(room_id, None)
        elif room_id in games:
            await broadcast(room_id)
