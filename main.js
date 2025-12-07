import {createBoard, playMove} from "./connect4.js"

window.addEventListener("DOMContentLoaded", () => {
    // initialize the UI
    const board = document.querySelector(".board");
    createBoard(board);
    // initialize websocket connection
    const websocket = new WebSocket(getWebSocketServer());
    initGame(websocket);
    receiveEvents(board, websocket);
    // enable to send moves if not spectator
    const params = new URLSearchParams(window.location.search);
    if (params.size === 0 || params.has("join")) {
        sendMoves(board, websocket);
    }
});

function initGame(websocket) {
    websocket.addEventListener("open", () => {
        const params = new URLSearchParams(window.location.search);
        let event = {"type": "init"};
        if (!params.has(watch)) {
            event.nickname = prompt("What is your nickname?");
        }
        if (params.has("join")) {
            event.join = params.get("join");
        } else if (params.has("watch")) {
            event.watch = params.get("watch");
        }
        console.log(`sending event ${JSON.stringify(event)}`);
        websocket.send(JSON.stringify(event));
    });
}

function sendMoves(board, websocket) {
    board.addEventListener("click", ({ target }) => {
        const column = target.dataset.column;
        if (column === undefined) {
            return;
        }
        const event = {
            type: "play",
            column: parseInt(column, 10),
        };
        websocket.send(JSON.stringify(event));
    });
}

function showMessage(message) {
    window.setTimeout(() => window.alert(message), 50);
}

function receiveEvents(board, websocket) {
    websocket.addEventListener("message", ({ data }) => {
        const event = JSON.parse(data);
        switch (event.type) {
            case "play":
                playMove(board, event.player, event.column, event.row);
                break;
            case "win":
                showMessage(`Player ${event.player} wins!`);
                websocket.close(1000);
                break;
            case "error":
                showMessage(event.message);
                break;
            case "init":
                document.querySelector(".join").href = "?join=" + event.join;
                document.querySelector(".watch").href = "?watch=" + event.watch;
                break;
            default:
                throw new Error(`Unsupported event type: ${event.type}`);
                
        }
    });
}

function getWebSocketServer() {
  if (window.location.host === "lucanijim.github.io") {
    return "wss://convincing-alleen-luca-personal-994e43bc.koyeb.app/";
  } else if (window.location.host === "localhost:8000") {
    return "ws://localhost:8001/";
  } else {
    throw new Error(`Unsupported host: ${window.location.host}`);
  }
}