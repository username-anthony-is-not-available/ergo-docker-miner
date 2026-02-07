import requests
import subprocess
import os
import logging

logger = logging.getLogger(__name__)

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

def get_normalized_miner_data():
    """Fetches data from the miner API and normalizes it."""
    miner = os.getenv('MINER', 'lolminer')
    api_port = 4444

    # Try with retries
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
                logger.warning(f"Attempt {attempt + 1} failed to fetch miner data: {e}. Retrying...")
                continue
            else:
                logger.error(f"Failed to fetch miner data after {max_retries} attempts: {e}")
                return None
    return None
