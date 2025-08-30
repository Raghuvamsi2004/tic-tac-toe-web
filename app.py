from flask import Flask, render_template, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a3f58b9c6f4d2b1e9c1f64dfe1234567'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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
    sid = request.sid if False else None  # placeholder to get sid from context
    # flask-socketio provides request implicitly
    from flask import request
    sid = request.sid

    if room_id not in rooms:
        rooms[room_id] = {'players': {}, 'board': ['']*9, 'turn': '❤️'}

    room = rooms[room_id]
    if len(room['players']) >= 2 and sid not in room['players']:
        emit('room_full')
        return

    # assign a symbol if new
    if sid not in room['players']:
        symbol = '❤️' if '❤️' not in room['players'].values() else '⭐'
        room['players'][sid] = symbol

    join_room(room_id)

    # prepare player list with simple info
    players = list(room['players'].values())
    emit('joined', {'symbol': room['players'][sid], 'players': players, 'board': room['board'], 'turn': room['turn']}, room=sid)
    emit('player_update', {'players': players}, room=room_id)

@socketio.on('make_move')
def handle_move(data):
    from flask import request
    sid = request.sid
    room_id = data['room']
    idx = int(data['index'])

    if room_id not in rooms: return
    room = rooms[room_id]
    symbol = room['players'].get(sid)
    # basic validations
    if not symbol: return
    if room['turn'] != symbol: 
        emit('invalid_move', {'reason':'not your turn'}, room=sid)
        return
    if room['board'][idx] != '':
        emit('invalid_move', {'reason':'cell taken'}, room=sid)
        return

    # apply move
    room['board'][idx] = symbol
    winner = check_winner(room['board'])
    # swap turn only if no winner/draw
    if winner is None:
        room['turn'] = '⭐' if room['turn'] == '❤️' else '❤️'
    # broadcast move to room
    emit('move_made', {'index': idx, 'symbol': symbol, 'board': room['board'], 'turn': room['turn']}, room=room_id)

    if winner:
        emit('game_over', {'winner': winner, 'board': room['board']}, room=room_id)
        # reset room after game (optional: keep for rematch)
        room['board'] = ['']*9
        room['turn'] = '❤️'

@socketio.on('leave_room')
def handle_leave(data):
    from flask import request
    sid = request.sid
    room_id = data['room']
    if room_id in rooms and sid in rooms[room_id]['players']:
        del rooms[room_id]['players'][sid]
        leave_room(room_id)
        emit('player_update', {'players': list(rooms[room_id]['players'].values())}, room=room_id)
        # if no players, clean up
        if not rooms[room_id]['players']:
            del rooms[room_id]

if __name__ == "__main__":
    # local development with eventlet
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

