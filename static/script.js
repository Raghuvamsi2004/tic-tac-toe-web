const socket = io();

const room = ROOM;
document.getElementById('share').value = window.location.href;

let mySymbol = null;
let board = Array(9).fill('');
let myTurn = false;

function renderBoard() {
    console.log('Rendering board:', board); // Debug
    const boardDiv = document.getElementById('board');
    boardDiv.innerHTML = '';
    board.forEach((cell, i) => {
        const d = document.createElement('div');
        d.className = 'cell' + (cell ? ' disabled' : '');
        d.innerHTML = cell || '';
        d.onclick = () => { 
            console.log(`Cell ${i} clicked, my turn: ${myTurn}, cell empty: ${!cell}`); // Debug
            if (!cell && myTurn) makeMove(i); 
        };
        boardDiv.appendChild(d);
    });
    
    // Update turn indicator styling
    const turnEl = document.getElementById('turn');
    if (myTurn) {
        turnEl.style.color = 'green';
        turnEl.innerHTML = `Turn: ${document.querySelector('#turn').textContent.split(':')[1]} (YOUR TURN!)`;
    } else {
        turnEl.style.color = 'red';
    }
}

function makeMove(i) {
    console.log(`Making move at ${i}`); // Debug
    socket.emit('make_move', { room, index: i });
}

function leave() {
    socket.emit('leave_room', { room });
    window.location = '/';
}

// Socket events
socket.on('connect', () => {
    console.log('Connected to server'); // Debug
    document.getElementById('status').innerText = 'Connected! Joining room...';
    document.getElementById('status').style.color = 'green';
    
    // Join room immediately after connection
    socket.emit('join_room', { room });
});

socket.on('disconnect', () => {
    console.log('Disconnected from server'); // Debug
    document.getElementById('status').innerText = 'Disconnected';
    document.getElementById('status').style.color = 'red';
});

socket.on('joined', (data) => {
    console.log('Joined room:', data); // Debug
    mySymbol = data.symbol;
    board = data.board;
    document.getElementById('status').innerText = 'Joined successfully!';
    document.getElementById('status').style.color = 'green';
    document.getElementById('players').innerText = 'Players: ' + (data.players.join(' , ') || 'waiting...');
    document.getElementById('turn').innerText = 'Turn: ' + data.turn;
    myTurn = (data.turn === mySymbol);
    renderBoard();
    alert('You joined! You are: ' + mySymbol);
});

socket.on('player_update', (data) => {
    console.log('Player update:', data); // Debug
    document.getElementById('players').innerText = 'Players: ' + (data.players.join(' , ') || 'waiting...');
    
    // Show status based on player count
    if (data.players.length === 1) {
        document.getElementById('status').innerText = 'Waiting for another player...';
        document.getElementById('status').style.color = 'orange';
    } else if (data.players.length === 2) {
        document.getElementById('status').innerText = 'Game ready! Both players connected.';
        document.getElementById('status').style.color = 'green';
    }
});

socket.on('move_made', (data) => {
    console.log('Move made:', data); // Debug
    board = data.board;  // Update the local board state
    document.getElementById('turn').innerText = 'Turn: ' + data.turn;
    myTurn = (data.turn === mySymbol);
    
    console.log(`Updated: myTurn=${myTurn}, mySymbol=${mySymbol}, currentTurn=${data.turn}`); // Debug
    
    renderBoard();  // Re-render the board with new state
});

socket.on('invalid_move', (data) => {
    console.log('Invalid move:', data); // Debug
    alert('Invalid move: ' + data.reason);
});

socket.on('room_full', () => {
    console.log('Room is full'); // Debug
    alert('Room is full. Can only have 2 players.');
    window.location = '/';
});

socket.on('game_over', (data) => {
    console.log('Game over:', data); // Debug
    if (data.winner === 'draw') {
        alert("It's a draw! 🤝");
    } else {
        alert(`${data.winner} wins! 🎉`);
    }
    // Auto-reset board for new game
    setTimeout(() => {
        board = Array(9).fill('');
        renderBoard();
        document.getElementById('turn').innerText = 'Turn: ❤️ (New game started!)';
        myTurn = (mySymbol === '❤️');
    }, 2000);
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error); // Debug
    document.getElementById('status').innerText = 'Connection failed!';
    document.getElementById('status').style.color = 'red';
});

// Initialize empty board on page load
renderBoard();