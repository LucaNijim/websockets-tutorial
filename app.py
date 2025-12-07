import asyncio
from websockets.asyncio.server import serve, broadcast
import json
import secrets
import http
import os 
import signal

from gamelogic.connect4 import PLAYER1, PLAYER2, Connect4
from structures.room import Room, PlayerInfo

JOIN = {}
WATCH = {}

async def play(websocket, room):
    game = room.game
    player = room.connections[websocket].role
    connected = room.connections.keys()
    specs = room.spectators
    async for message in websocket:
        event_in = json.loads(message)
        print('Received event:', event_in)
        if event_in["type"] == "play":
            print(f'Event type: play')
            print(f'Player {player}')
            try:
                row = game.play(player, event_in["column"])
                broadcast(connected | specs, json.dumps({
                        "type": "play", 
                        "row": row, 
                        "column": event_in["column"], 
                        "player": player}))
                
                if game.winner is not None:
                    room.game_over = True
                    
                    broadcast(connected, json.dumps({
                            "type": "win", 
                            "winner": game.winner, 
                            "message": f"Game Over! Winner is {game.winner}"
                        }))
                    
                    
            except ValueError as e:
                await websocket.send(json.dumps({"type": "error", "message": str(e)}))
        else:
            raise Exception(f"Unexpected event type: {event_in['type']}")

async def catchup(websocket, game):
    print('Running catchup')
    for move in game.moves:
        event = {
            "type": "play",
            "player": move[0], 
            "column": move[1], 
            "row": move[2], 
        }
        await websocket.send(json.dumps(event))

async def error(websocket, message):
    event = {
        "type": "error",
        "message": message
    }
    await websocket.send(json.dumps(event))
    
async def start_room(websocket, event1):
    # initialize room 
    room = Room()
    nickname = "player_1"
    room.connections[websocket] = PlayerInfo(PLAYER1, nickname)
    # add this to global dict
    join_key = secrets.token_urlsafe(8)
    watch_key = room.watch_key
    JOIN[join_key] = room
    WATCH[room.watch_key] = room
    
    try:
        # send secret to client
        # so they can invite their friends
        print(f'sending init event')
        event = {
            "type": "init",
            "join_key": join_key, 
            "watch_key": watch_key
        }
        await websocket.send(json.dumps(event))
        
        # temp ( for testing )
        print(f"First player, {nickname}, started game at {join_key}")
        await play(
            websocket, 
            room)
    finally:
        # clear the join thing to avoid memory leaks
        print(f"Player 1 exiting game at {join_key}")
        del JOIN[join_key]
    
async def join_room(websocket, event1):
    # find game
    join_key, nickname = event1["join"], "player_2"
    try:
        room = JOIN[join_key]
    except KeyError:
        await error(websocket, f"No join key {join_key}")
        return
    
    # register to add
    room.connections[websocket] = PlayerInfo(PLAYER2, nickname)
    try: 
        # testing
        print(f"Second player, {nickname}, joined game {id(room)} at {join_key}")
        event = {
            "type": "init",
            "watch_key": room.watch_key
        }
        await websocket.send(json.dumps(event))
        await catchup(websocket, room.game)
        await play(
            websocket, 
            room)
    finally:
        print(f"Player 2 exiting game at {join_key}")
        del room.connections[websocket]

async def watch(websocket, watch_key):
    try:
        room = WATCH[watch_key]
    except KeyError:
        await error(websocket, f"No watch key {watch_key}")
        return
    
    room.spectators.add(websocket)
    try:
        print(f"Spectator joined room {id(room)} at {watch_key}")
        await catchup(websocket, room.game)
        await websocket.wait_closed()
    finally:
        print(f"Spectator exiting game at {watch_key}")
        room.spectators.remove(websocket)

async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    if event["type"] == "init":
        assert event["type"] == "init"
        
        if "join" in event:
            await join_room(websocket, event) 
        elif "watch" in event:
            await watch(websocket, event["watch"])
        else:
            # first player starts
            await start_room(websocket, event)

def health_check(connection, request):
    print(f"Health check request from {connection}")
    print(f"Request: {request}")
    if request.path == "/healthz":
        return connection.respond(http.HTTPStatus.OK, "OK\n")
    return None

async def main():
    port = int(os.environ.get("PORT", "8001"))
    print(f"Listening on port {port}")
    async with serve(handler, "", port, process_request=health_check) as server:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, server.close)
        await server.wait_closed()


if __name__ == '__main__':
    asyncio.run(main())