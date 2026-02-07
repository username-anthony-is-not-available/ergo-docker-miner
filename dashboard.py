from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import requests
import time
from threading import Thread
import os
import database

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

@app.route('/config')
def config():
    return render_template('config.html')

def read_env_file():
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

def write_env_file(env_vars):
    with open('.env', 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    if request.method == 'POST':
        data = request.json
        env_vars = read_env_file()
        for key, value in data.items():
            env_vars[key] = value
        write_env_file(env_vars)
        return jsonify({'message': 'Configuration saved successfully!'})
    else:
        return jsonify(read_env_file())

@app.route('/api/restart', methods=['POST'])
def restart():
    os.system('./restart.sh')
    return jsonify({'message': 'Restarting...'})

@app.route('/hashrate-history')
def hashrate_history():
    history = database.get_history()
    return jsonify(history)

@socketio.on('connect')
def handle_connect():
    """Sends the initial data to the client upon connection."""
    if miner_data:
        emit('update', miner_data)

if __name__ == '__main__':
    database.init_db()
    thread = Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
