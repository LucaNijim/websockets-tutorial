import asyncio
from websockets.asyncio.server import serve, broadcast
import json
import secrets

from connect4 import PLAYER1, PLAYER2, Connect4


JOIN = {}
WATCH = {}

async def play(websocket, game, player, connected):
    async for message in websocket:
        event_in = json.loads(message)
        print('Recieved event:', event_in)
        if event_in["type"] == "play":
            print(f'Event type: play')
            print(f'Player {player}')
            try:
                row = game.play(player, event_in["column"])
                broadcast(connected, json.dumps({
                        "type": "play", 
                        "row": row, 
                        "column": event_in["column"], 
                        "player": player}))
                
                if game.winner is not None:
                    broadcast(connected, json.dumps({
                            "type": "win", 
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

async def start(websocket):
    # initialize game 
    game = Connect4()
    # initialize set of connecteds
    connected = {websocket}
    # add this to global dict
    join_key = secrets.token_urlsafe(8)
    watch_key = secrets.token_urlsafe(8)
    JOIN[join_key] = game, connected
    WATCH[watch_key] = game, connected
    
    try:
        # send secret to client
        # so they can invite their friends
        event = {
            "type": "init",
            "join": join_key, 
            "watch": watch_key
        }
        await websocket.send(json.dumps(event))
        
        # temp ( for testing )
        print(f"First player started game at {join_key}")
        await play(websocket, game, PLAYER1, connected)
    finally:
        # clear the join thing to avoid memory leaks
        print(f"Player 1 exiting game at {join_key}")
        del JOIN[join_key]

async def error(websocket, message):
    event = {
        "type": "error",
        "message": message
    }
    await websocket.send(json.dumps(event))
    
async def join(websocket, join_key):
    # find game
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, f"No join key {join_key}")
        return
    
    # register to add
    connected.add(websocket)
    try: 
        # testing
        print(f"Second player joined game {id(game)} at {join_key}")
        await catchup(websocket, game)
        await play(websocket, game, PLAYER2, connected)
    finally:
        print(f"Player 2 exiting game at {join_key}")
        connected.remove(websocket)

async def watch(websocket, watch_key):
    try:
        game, connected = WATCH[watch_key]
    except KeyError:
        await error(websocket, f"No watch key {watch_key}")
        return
    
    connected.add(websocket)
    try:
        print(f"Spectator joined game {id(game)} at {watch_key}")
        await catchup(websocket, game)
        await websocket.wait_closed()
    finally:
        print(f"Spectator exiting game at {watch_key}")
        connected.remove(websocket)


async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "init"
    
    if "join" in event:
        await join(websocket, event["join"])
    elif "watch" in event:
        await watch(websocket, event["watch"])
    else:
        # first player starts
        await start(websocket)

async def main():
    async with serve(handler, "", 8001) as server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())