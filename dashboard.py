from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import requests
import time
from threading import Thread
import os
import subprocess
import database
import logging
from miner_api import get_gpu_smi_data, get_normalized_miner_data

app = Flask(__name__)
socketio = SocketIO(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = app.logger

# Global variable to store the latest miner data
miner_data = {
    'status': 'Starting...'
}

def background_thread():
    """Continuously fetches and broadcasts miner data."""
    while True:
        global miner_data
        try:
            data = get_normalized_miner_data()
            if data:
                # Merge with SMI data
                smi_data = get_gpu_smi_data()
                if smi_data:
                    for i, gpu in enumerate(data['gpus']):
                        if i < len(smi_data):
                            # Only overwrite if SMI data is non-zero (SMI is more reliable for temp/power)
                            if smi_data[i]['temperature'] > 0:
                                gpu['temperature'] = smi_data[i]['temperature']
                            if smi_data[i]['power_draw'] > 0:
                                gpu['power_draw'] = smi_data[i]['power_draw']

                # Calculate total power and average temperature
                total_power = 0
                total_temp = 0
                gpu_count = len(data['gpus'])

                for gpu in data['gpus']:
                    total_power += gpu.get('power_draw', 0)
                    total_temp += gpu.get('temperature', 0)

                data['total_power_draw'] = total_power
                data['avg_temperature'] = total_temp / gpu_count if gpu_count > 0 else 0

                # Determine status based on hashrate
                if data['total_hashrate'] > 0:
                    data['status'] = 'Mining'
                else:
                    data['status'] = 'Idle/Connecting'

                miner_data = data
                socketio.emit('update', miner_data)
            else:
                miner_data['status'] = 'Error: Miner API unreachable'
                socketio.emit('update', miner_data)
        except Exception as e:
            logger.error(f"Error in background thread: {e}")
            miner_data['status'] = f"Error: {str(e)}"
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
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        key, value = parts
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
    try:
        subprocess.run(['./restart.sh'], check=True)
        return jsonify({'message': 'Restarting...'})
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing restart script: {e}")
        return jsonify({'message': 'Restart failed!'}), 500

@app.route('/hashrate-history')
def hashrate_history():
    history = database.get_history()
    return jsonify(history)

@app.route('/api/logs')
def get_logs():
    try:
        if os.path.exists('miner.log'):
            # Return last 100 lines using tail-like logic for efficiency
            with open('miner.log', 'r') as f:
                # For simplicity with small files, we can just readlines.
                # For very large logs, this might be slow, but miner.log is usually rotated or small in Docker.
                lines = f.readlines()
                return jsonify({'logs': ''.join(lines[-100:])})
        else:
            return jsonify({'logs': 'Miner log file not found. Waiting for miner to start...'})
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return jsonify({'error': str(e)}), 500

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
