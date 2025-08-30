from flask import Flask, render_template, redirect, url_for, request
from flask_socketio import SocketIO, join_room, leave_room, emit
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a3f58b9c6f4d2b1e9c1f64dfe1234567'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Keep simple server-side room state (not persistent). Each room holds:
# { 'players': { sid: symbol }, 'board': ['']*9, 'turn': '❤️' }
rooms = {}

def check_winner(board):
    wins = [(0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return 'draw'
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/room/<room_id>")
def room(room_id):
    return render_template("room.html", room_id=room_id)

@app.route("/create")
def create():
    room_id = str(uuid.uuid4())[:8]
    return redirect(url_for('room', room_id=room_id))

# Socket events
@socketio.on('join_room')
def handle_join(data):
    room_id = data.get('room')
    name = data.get('name', 'Guest')
    sid = request.sid

    print(f"Player {sid} joining room {room_id}")  # Debug

    if room_id not in rooms:
        rooms[room_id] = {'players': {}, 'board': ['']*9, 'turn': '❤️'}
        print(f"Created new room {room_id}")  # Debug

    room = rooms[room_id]
    
    # Check if room is full
    if len(room['players']) >= 2 and sid not in room['players']:
        print(f"Room {room_id} is full")  # Debug
        emit('room_full')
        return

    # Assign a symbol if new player
    if sid not in room['players']:
        symbol = '❤️' if '❤️' not in room['players'].values() else '⭐'
        room['players'][sid] = symbol
        print(f"Assigned symbol {symbol} to player {sid}")  # Debug

    join_room(room_id)

    # Prepare player list with simple info
    players = list(room['players'].values())
    print(f"Current players in room {room_id}: {players}")  # Debug
    
    # Send joined confirmation to the player
    emit('joined', {
        'symbol': room['players'][sid], 
        'players': players, 
        'board': room['board'], 
        'turn': room['turn']
    })
    
    # Update all players in the room about player list
    socketio.emit('player_update', {'players': players}, room=room_id)

@socketio.on('make_move')
def handle_move(data):
    sid = request.sid
    room_id = data['room']
    idx = int(data['index'])

    print(f"Move attempt by {sid} in room {room_id} at index {idx}")  # Debug

    if room_id not in rooms: 
        print(f"Room {room_id} not found")  # Debug
        return
        
    room = rooms[room_id]
    symbol = room['players'].get(sid)
    
    # Basic validations
    if not symbol: 
        print(f"Player {sid} not found in room")  # Debug
        return
        
    if room['turn'] != symbol: 
        print(f"Not {symbol}'s turn, current turn: {room['turn']}")  # Debug
        emit('invalid_move', {'reason': 'Not your turn'})
        return
        
    if room['board'][idx] != '':
        print(f"Cell {idx} already taken")  # Debug
        emit('invalid_move', {'reason': 'Cell already taken'})
        return

    # Apply move
    room['board'][idx] = symbol
    winner = check_winner(room['board'])
    
    # Swap turn only if no winner/draw
    if winner is None:
        room['turn'] = '⭐' if room['turn'] == '❤️' else '❤️'
        
    print(f"Move applied: {symbol} at {idx}, winner: {winner}, next turn: {room['turn']}")  # Debug

    # Broadcast move to room
    socketio.emit('move_made', {
        'index': idx, 
        'symbol': symbol, 
        'board': room['board'], 
        'turn': room['turn']
    }, room=room_id)

    if winner:
        print(f"Game over, winner: {winner}")  # Debug
        socketio.emit('game_over', {'winner': winner, 'board': room['board']}, room=room_id)
        # Reset room after game
        room['board'] = ['']*9
        room['turn'] = '❤️'

@socketio.on('leave_room')
def handle_leave(data):
    sid = request.sid
    room_id = data['room']
    
    print(f"Player {sid} leaving room {room_id}")  # Debug
    
    if room_id in rooms and sid in rooms[room_id]['players']:
        del rooms[room_id]['players'][sid]
        leave_room(room_id)
        socketio.emit('player_update', {
            'players': list(rooms[room_id]['players'].values())
        }, room=room_id)
        
        # If no players, clean up
        if not rooms[room_id]['players']:
            print(f"Room {room_id} is empty, deleting")  # Debug
            del rooms[room_id]

@socketio.on('connect')
def handle_connect():
    print(f"Client {request.sid} connected")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client {request.sid} disconnected")
    # Clean up player from all rooms
    for room_id, room_data in list(rooms.items()):
        if request.sid in room_data['players']:
            del room_data['players'][request.sid]
            socketio.emit('player_update', {
                'players': list(room_data['players'].values())
            }, room=room_id)
            if not room_data['players']:
                del rooms[room_id]

if __name__ == "__main__":
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=False, host=host, port=port)
