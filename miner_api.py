import requests
import subprocess
import os
import logging
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

def get_gpu_names() -> List[str]:
    """Fetches GPU names from nvidia-smi or rocm-smi."""
    gpu_names = []
    try:
        subprocess.check_output(['which', 'nvidia-smi'], stderr=subprocess.DEVNULL)
        output = subprocess.check_output(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], stderr=subprocess.DEVNULL).decode()
        gpu_names = [line.strip() for line in output.strip().split('\n') if line.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.check_output(['which', 'rocm-smi'], stderr=subprocess.DEVNULL)
            # rocm-smi --showname --csv
            output = subprocess.check_output("rocm-smi --showname --csv | tail -n +2", shell=True, stderr=subprocess.DEVNULL).decode()
            for line in output.strip().split('\n'):
                if not line.strip(): continue
                parts = line.split(',')
                if len(parts) >= 2:
                    gpu_names.append(parts[1].strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return gpu_names

def get_gpu_smi_data() -> List[Dict[str, float]]:
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
            # rocm-smi's csv output includes a header, so we skip it with tail
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

def _fetch_single_miner_data(miner: str, api_port: int) -> Optional[Dict[str, Any]]:
    """Fetches data from a single miner API instance."""
    max_retries = 3
    for attempt in range(max_retries):
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
                        'temperature': 0,
                        'power_draw': 0
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
                    'total_dual_hashrate': 0,
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
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed to fetch miner data on port {api_port}: {e}. Retrying...")
                continue
            else:
                logger.error(f"Failed to fetch miner data on port {api_port} after {max_retries} attempts: {e}")
                return None
    return None

def get_normalized_miner_data() -> Optional[Dict[str, Any]]:
    """Fetches data from the miner API and normalizes it, supporting multi-process mode."""
    miner = os.getenv('MINER', 'lolminer')
    api_port = int(os.getenv('API_PORT', 4444))
    multi_process = os.getenv('MULTI_PROCESS', 'false').lower() == 'true'
    gpu_devices_env = os.getenv('GPU_DEVICES', 'AUTO')

    if multi_process and gpu_devices_env != 'AUTO':
        device_ids = [d.strip() for d in gpu_devices_env.split(',') if d.strip()]
        aggregated_data = None

        for i, device_id in enumerate(device_ids):
            current_port = api_port + i
            data = _fetch_single_miner_data(miner, current_port)
            if data:
                # Map back to original GPU index
                # In multi-process mode, each miner has 1 GPU, usually index 0 in its API
                for gpu in data['gpus']:
                    gpu['index'] = int(device_id)

                if aggregated_data is None:
                    aggregated_data = data
                else:
                    aggregated_data['total_hashrate'] += data['total_hashrate']
                    aggregated_data['total_dual_hashrate'] += data['total_dual_hashrate']
                    aggregated_data['uptime'] = min(aggregated_data['uptime'], data['uptime'])
                    aggregated_data['gpus'].extend(data['gpus'])

        # Ensure GPUs are sorted by index
        if aggregated_data:
            aggregated_data['gpus'].sort(key=lambda x: x['index'])
        return aggregated_data
    else:
        return _fetch_single_miner_data(miner, api_port)

def get_full_miner_data() -> Optional[Dict[str, Any]]:
    """Fetches miner and SMI data, merges them, and calculates aggregates."""
    data = get_normalized_miner_data()
    if not data:
        return None

    smi_data = get_gpu_smi_data()
    if smi_data:
        for i, gpu in enumerate(data['gpus']):
            if i < len(smi_data):
                # Only overwrite if SMI data is non-zero (SMI is more reliable for temp/power)
                if smi_data[i]['temperature'] > 0:
                    gpu['temperature'] = smi_data[i]['temperature']
                if smi_data[i]['power_draw'] > 0:
                    gpu['power_draw'] = smi_data[i]['power_draw']

    # Calculate aggregates
    total_power = 0
    total_temp = 0
    total_accepted = 0
    total_rejected = 0
    total_fan = 0
    gpu_count = len(data['gpus'])

    for gpu in data['gpus']:
        total_power += gpu.get('power_draw', 0)
        total_temp += gpu.get('temperature', 0)
        total_accepted += gpu.get('accepted_shares', 0)
        total_rejected += gpu.get('rejected_shares', 0)
        total_fan += gpu.get('fan_speed', 0)

    data['total_power_draw'] = total_power
    data['avg_temperature'] = total_temp / gpu_count if gpu_count > 0 else 0
    data['total_accepted_shares'] = total_accepted
    data['total_rejected_shares'] = total_rejected
    data['avg_fan_speed'] = total_fan / gpu_count if gpu_count > 0 else 0
    data['timestamp'] = time.time()

    # Determine status
    if data['total_hashrate'] > 0:
        data['status'] = 'Mining'
    else:
        data['status'] = 'Idle'

    return data
