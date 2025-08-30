const socket = io();

const room = ROOM;
document.getElementById('share').value = window.location.href;

let mySymbol = null;
let board = Array(9).fill('');
let myTurn = false;

function renderBoard(){
  const boardDiv = document.getElementById('board');
  boardDiv.innerHTML = '';
  board.forEach((cell, i) => {
    const d = document.createElement('div');
    d.className = 'cell' + (cell ? ' disabled' : '');
    d.innerHTML = cell || '';
    d.onclick = () => { if (!cell && myTurn) makeMove(i); };
    boardDiv.appendChild(d);
  });
}

function makeMove(i){
  socket.emit('make_move', { room, index: i });
}

function leave(){
  socket.emit('leave_room', { room });
  window.location = '/';
}

// Socket events
socket.on('connect', () => {
  document.getElementById('status').innerText = 'Connected';
  // ask server to join room
  socket.emit('join_room', { room });
});

socket.on('joined', (data) => {
  mySymbol = data.symbol;
  board = data.board;
  document.getElementById('players').innerText = 'Players: ' + (data.players.join(' , ') || 'waiting...');
  document.getElementById('turn').innerText = 'Turn: ' + data.turn;
  myTurn = (data.turn === mySymbol);
  renderBoard();
  alert('You are: ' + mySymbol);
});

socket.on('player_update', (data) => {
  document.getElementById('players').innerText = 'Players: ' + (data.players.join(' , '));
});

socket.on('move_made', (data) => {
  board = data.board;
  document.getElementById('turn').innerText = 'Turn: ' + data.turn;
  myTurn = (data.turn === mySymbol);
  renderBoard();
});

socket.on('invalid_move', (data) => {
  alert('Invalid move: ' + data.reason);
});

socket.on('room_full', () => {
  alert('Room is full. Can only have 2 players.');
  window.location = '/';
});

socket.on('game_over', (data) => {
  if (data.winner === 'draw') {
    alert("It's a draw! ❤️");
  } else {
    alert(`${data.winner} wins!`);
  }
});
