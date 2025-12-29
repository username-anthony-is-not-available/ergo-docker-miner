from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import requests
import time
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app)

# Global variable to store the latest miner data
miner_data = {}

def get_miner_data():
    """Fetches data from the lolMiner API."""
    try:
        response = requests.get('http://localhost:4444/')
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, ValueError):
        return None

def background_thread():
    """Continuously fetches and broadcasts miner data."""
    while True:
        global miner_data
        data = get_miner_data()
        if data:
            miner_data = data
            socketio.emit('update', miner_data)
        time.sleep(5)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Sends the initial data to the client upon connection."""
    if miner_data:
        emit('update', miner_data)

if __name__ == '__main__':
    thread = Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
