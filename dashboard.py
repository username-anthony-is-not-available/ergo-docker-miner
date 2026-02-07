from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import requests
import time
from threading import Thread
import os
import subprocess
import database
import logging

app = Flask(__name__)
socketio = SocketIO(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = app.logger

# Global variable to store the latest miner data
miner_data = {}

def get_gpu_smi_data():
    """Fetches GPU stats from nvidia-smi or rocm-smi."""
    gpu_stats = []
    is_nvidia = False
    smi_cmd = ""

    try:
        subprocess.check_output(['which', 'nvidia-smi'], stderr=subprocess.DEVNULL)
        smi_cmd = "nvidia-smi --query-gpu=temperature.gpu,power.draw --format=csv,noheader,nounits"
        is_nvidia = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.check_output(['which', 'rocm-smi'], stderr=subprocess.DEVNULL)
            smi_cmd = "rocm-smi --showtemp --showpower --csv | tail -n +2"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    if smi_cmd:
        try:
            smi_output = subprocess.check_output(smi_cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            for line in smi_output.strip().split('\n'):
                if not line.strip(): continue
                try:
                    if is_nvidia:
                        temp, power = map(float, line.split(', '))
                        gpu_stats.append({'temperature': temp, 'power_draw': power})
                    else: # AMD
                        parts = line.split(',')
                        # rocm-smi csv: card,temp,power
                        temp = float(parts[1])
                        power = float(parts[2].replace('W', '').strip())
                        gpu_stats.append({'temperature': temp, 'power_draw': power})
                except (ValueError, IndexError):
                    gpu_stats.append({'temperature': 0, 'power_draw': 0})
        except subprocess.CalledProcessError:
            pass
    return gpu_stats

def get_normalized_miner_data():
    """Fetches data from the miner API and normalizes it."""
    miner = os.getenv('MINER', 'lolminer')
    api_port = 4444

    try:
        if miner == 'lolminer':
            response = requests.get(f'http://localhost:{api_port}/', timeout=2)
            response.raise_for_status()
            data = response.json()

            total_perf = data.get('Total_Performance', [0])
            normalized = {
                'miner': 'lolminer',
                'uptime': data.get('Session', {}).get('Uptime', 0),
                'total_hashrate': total_perf[0],
                'total_dual_hashrate': total_perf[1] if len(total_perf) > 1 else 0,
                'gpus': []
            }

            for i, gpu in enumerate(data.get('GPUs', [])):
                perf = gpu.get('Performance', [0])
                gpu_hashrate = perf[0] if isinstance(perf, list) else perf
                gpu_dual_hashrate = perf[1] if isinstance(perf, list) and len(perf) > 1 else 0

                normalized['gpus'].append({
                    'index': i,
                    'hashrate': gpu_hashrate,
                    'dual_hashrate': gpu_dual_hashrate,
                    'fan_speed': gpu.get('Fan_Speed', 0),
                    'accepted_shares': gpu.get('Accepted_Shares', 0),
                    'rejected_shares': gpu.get('Rejected_Shares', 0),
                    'temperature': 0, # To be filled by SMI
                    'power_draw': 0   # To be filled by SMI
                })
            return normalized

        elif miner == 't-rex':
            response = requests.get(f'http://localhost:{api_port}/summary', timeout=2)
            response.raise_for_status()
            data = response.json()

            normalized = {
                'miner': 't-rex',
                'uptime': data.get('uptime', 0),
                'total_hashrate': data.get('hashrate', 0) / 1000000,
                'total_dual_hashrate': 0, # T-Rex dual not supported in this dashboard yet
                'gpus': []
            }

            for i, gpu in enumerate(data.get('gpus', [])):
                shares = gpu.get('shares', {})
                normalized['gpus'].append({
                    'index': i,
                    'hashrate': gpu.get('hashrate', 0) / 1000000,
                    'dual_hashrate': 0,
                    'fan_speed': gpu.get('fan_speed', 0),
                    'accepted_shares': shares.get('accepted_count', 0),
                    'rejected_shares': shares.get('rejected_count', 0),
                    'temperature': gpu.get('temperature', 0),
                    'power_draw': gpu.get('power', 0)
                })
            return normalized

    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Error fetching miner data: {e}")
        return None

    return None

def background_thread():
    """Continuously fetches and broadcasts miner data."""
    while True:
        global miner_data
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
