import { createBoard, playMove } from "./connect4.js"

window.addEventListener("DOMContentLoaded", () => {
    // initialize the UI
    const board = document.querySelector(".board");
    createBoard(board);
    // initialize websocket connection
    const websocket = new WebSocket("ws://localhost:8001/");
    sendMoves(board, websocket);
});

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