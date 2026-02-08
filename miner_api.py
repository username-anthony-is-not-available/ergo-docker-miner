import requests
import re
import subprocess
import os
import logging
from typing import List, Dict, Any, Optional
import time
import psutil

logger = logging.getLogger(__name__)

# Module-level cache for GPU names
_gpu_names_cache: List[str] = []

def _is_mock_enabled() -> bool:
    """Checks if the GPU mock mode is enabled via environment variable."""
    return os.getenv('GPU_MOCK', 'false').lower() == 'true'

def get_node_status() -> Dict[str, Any]:
    """Checks the sync status of a local Ergo node."""
    node_url = os.getenv('NODE_URL', 'http://localhost:9053')
    check_enabled = os.getenv('CHECK_NODE_SYNC', 'false').lower() == 'true'

    if not check_enabled:
        return {'is_synced': True, 'full_height': 0, 'headers_height': 0, 'enabled': False}

    try:
        response = requests.get(f"{node_url}/info", timeout=5)
        response.raise_for_status()
        data = response.json()

        full_height = data.get('fullHeight')
        headers_height = data.get('headersHeight')

        # Robust check: if fullHeight is null or less than headersHeight, it's not synced
        is_synced = False
        if full_height is not None and headers_height is not None:
            if full_height >= headers_height and full_height > 0:
                is_synced = True

        return {
            'is_synced': is_synced,
            'full_height': full_height,
            'headers_height': headers_height,
            'enabled': True,
            'error': None
        }
    except Exception as e:
        logger.error(f"Error checking node status: {e}")
        return {
            'is_synced': False,
            'full_height': None,
            'headers_height': None,
            'enabled': True,
            'error': str(e)
        }

def get_services_status() -> Dict[str, str]:
    """Checks if background services are running."""
    services = {
        'metrics.py': 'Stopped',
        'profit_switcher.py': 'Stopped',
        'cuda_monitor.sh': 'Stopped'
    }
    try:
        for proc in psutil.process_iter(['cmdline']):
            cmdline = proc.info.get('cmdline')
            if not cmdline:
                continue
            cmd_str = " ".join(cmdline)
            for service in services.keys():
                if service in cmd_str:
                    services[service] = 'Running'
    except Exception as e:
        logger.error(f"Error checking services status: {e}")

    # Check if cuda_monitor is even supposed to be running
    if os.getenv('AUTO_RESTART_ON_CUDA_ERROR', 'false').lower() != 'true':
        services['cuda_monitor.sh'] = 'Disabled'

    return services

def restart_service(service_name: str) -> bool:
    """Attempts to restart a background service."""
    allowed_services = {
        'metrics.py': 'python3 metrics.py',
        'profit_switcher.py': 'python3 profit_switcher.py',
        'cuda_monitor.sh': './cuda_monitor.sh'
    }

    if service_name not in allowed_services:
        return False

    try:
        # 1. Kill existing process(es)
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.info.get('cmdline')
                if cmdline and any(service_name in arg for arg in cmdline):
                    # Don't kill ourselves if we are the dashboard
                    if 'dashboard.py' in " ".join(cmdline):
                        continue
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 2. Start new instance
        cmd = allowed_services[service_name]
        # Use Popen with start_new_session to ensure it lives beyond the dashboard request
        subprocess.Popen(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {e}")
        return False

def get_system_info() -> Dict[str, Any]:
    """Fetches system info (CPU, RAM, Disk)."""
    try:
        return {
            'cpu_usage': psutil.cpu_percent(interval=0.1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'host_uptime': time.time() - psutil.boot_time(),
            'services': get_services_status()
        }
    except Exception as e:
        logger.error(f"Error fetching system info: {e}")
        return {
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'host_uptime': 0
        }

def get_gpu_names() -> List[str]:
    """Fetches GPU names from nvidia-smi or rocm-smi."""
    if _is_mock_enabled():
        return ["Mock NVIDIA GeForce RTX 3080", "Mock NVIDIA GeForce RTX 3080"]

    global _gpu_names_cache
    if _gpu_names_cache:
        return _gpu_names_cache

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

    if gpu_names:
        _gpu_names_cache = gpu_names
    return gpu_names

def get_gpu_smi_data() -> List[Dict[str, float]]:
    """Fetches GPU stats from nvidia-smi or rocm-smi."""
    if _is_mock_enabled():
        return [
            {'temperature': 60.0, 'power_draw': 200.0, 'fan_speed': 50.0},
            {'temperature': 62.0, 'power_draw': 210.0, 'fan_speed': 55.0}
        ]

    gpu_stats = []
    is_nvidia = False
    smi_cmd = ""

    try:
        subprocess.check_output(['which', 'nvidia-smi'], stderr=subprocess.DEVNULL)
        smi_cmd = "nvidia-smi --query-gpu=temperature.gpu,power.draw,fan.speed --format=csv,noheader,nounits"
        is_nvidia = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.check_output(['which', 'rocm-smi'], stderr=subprocess.DEVNULL)
            # rocm-smi's csv output: card,temperature,power,fan
            smi_cmd = "rocm-smi --showtemp --showpower --showfan --csv | tail -n +2"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    if smi_cmd:
        try:
            smi_output = subprocess.check_output(smi_cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            for line in smi_output.strip().split('\n'):
                if not line.strip(): continue
                try:
                    if is_nvidia:
                        parts = line.split(', ')
                        temp = float(parts[0])
                        power = float(parts[1])
                        fan = float(parts[2]) if len(parts) > 2 else 0
                        gpu_stats.append({'temperature': temp, 'power_draw': power, 'fan_speed': fan})
                    else: # AMD
                        parts = line.split(',')
                        # rocm-smi csv: card,temp,power,fan
                        temp = float(parts[1])
                        power = float(parts[2].replace('W', '').strip())
                        fan = float(parts[3]) if len(parts) > 3 else 0
                        gpu_stats.append({'temperature': temp, 'power_draw': power, 'fan_speed': fan})
                except (ValueError, IndexError):
                    gpu_stats.append({'temperature': 0, 'power_draw': 0, 'fan_speed': 0})
        except subprocess.CalledProcessError:
            pass
    return gpu_stats

def parse_lolminer_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parses raw lolMiner API response into a normalized format."""
    session = data.get('Session', {})
    total_perf = data.get('Total_Performance', [0])

    # Extract major driver version using regex from confirmed 'Driver' field
    driver_str = session.get('Driver', '')
    driver_version = "unknown"
    if driver_str:
        match = re.search(r'^(\d+)', driver_str)
        if match:
            driver_version = match.group(1)

    normalized = {
        'miner': 'lolminer',
        'uptime': session.get('Uptime', 0),
        'total_hashrate': total_perf[0] if total_perf else 0,
        'total_dual_hashrate': total_perf[1] if len(total_perf) > 1 else 0,
        'driver_version': driver_version,
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

def _fetch_single_miner_data(miner: str, api_port: int) -> Optional[Dict[str, Any]]:
    """Fetches data from a single miner API instance."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if miner == 'lolminer':
                response = requests.get(f'http://localhost:{api_port}/', timeout=2)
                response.raise_for_status()
                return parse_lolminer_data(response.json())

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

    if multi_process:
        if gpu_devices_env == 'AUTO':
            # Robust fallback: if MULTI_PROCESS is on but devices are AUTO,
            # we try to resolve them here to know how many API ports to query.
            try:
                output = subprocess.check_output(['nvidia-smi', '--query-gpu=index', '--format=csv,noheader'], stderr=subprocess.DEVNULL).decode()
                device_ids = [line.strip() for line in output.strip().split('\n') if line.strip()]
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    output = subprocess.check_output("rocm-smi --showtemp --csv | tail -n +2 | cut -d, -f1", shell=True, stderr=subprocess.DEVNULL).decode()
                    device_ids = [line.strip() for line in output.strip().split('\n') if line.strip()]
                except:
                    device_ids = []
        else:
            device_ids = [d.strip() for d in gpu_devices_env.split(',') if d.strip()]

        if not device_ids:
            # Fallback to single port if we couldn't determine devices
            return _fetch_single_miner_data(miner, api_port)

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

def _get_mock_full_data() -> Dict[str, Any]:
    """Generates realistic mock data for testing."""
    gpus = []
    num_gpus = 2
    for i in range(num_gpus):
        hashrate = 120.5 + i * 10
        power = 200.0 + i * 10
        gpus.append({
            'index': i,
            'hashrate': hashrate,
            'dual_hashrate': 0.0,
            'fan_speed': 50.0 + i * 5,
            'accepted_shares': 100 + i * 20,
            'rejected_shares': i,
            'temperature': 60.0 + i * 2,
            'power_draw': power,
            'efficiency': hashrate / power if power > 0 else 0
        })

    total_hashrate = sum(g['hashrate'] for g in gpus)
    total_power = sum(g['power_draw'] for g in gpus)

    return {
        'miner': 'lolminer (mock)',
        'uptime': 3600,
        'total_hashrate': total_hashrate,
        'total_dual_hashrate': 0.0,
        'gpus': gpus,
        'total_power_draw': total_power,
        'efficiency': total_hashrate / total_power if total_power > 0 else 0,
        'avg_temperature': sum(g['temperature'] for g in gpus) / num_gpus,
        'total_accepted_shares': sum(g['accepted_shares'] for g in gpus),
        'total_rejected_shares': sum(g['rejected_shares'] for g in gpus),
        'avg_fan_speed': sum(g['fan_speed'] for g in gpus) / num_gpus,
        'timestamp': time.time(),
        'status': 'Mining'
    }

def get_full_miner_data() -> Optional[Dict[str, Any]]:
    """Fetches miner and SMI data, merges them, and calculates aggregates."""
    if _is_mock_enabled():
        return _get_mock_full_data()

    data = get_normalized_miner_data()
    if not data:
        return None

    smi_data = get_gpu_smi_data()
    if smi_data:
        for i, gpu in enumerate(data['gpus']):
            if i < len(smi_data):
                # Only overwrite if SMI data is non-zero (SMI is more reliable for temp/power/fan)
                if smi_data[i]['temperature'] > 0:
                    gpu['temperature'] = smi_data[i]['temperature']
                if smi_data[i]['power_draw'] > 0:
                    gpu['power_draw'] = smi_data[i]['power_draw']
                if smi_data[i].get('fan_speed', 0) > 0:
                    gpu['fan_speed'] = smi_data[i]['fan_speed']

    # Calculate aggregates
    total_power = 0
    total_temp = 0
    total_accepted = 0
    total_rejected = 0
    total_fan = 0
    gpu_count = len(data['gpus'])

    for gpu in data['gpus']:
        # Calculate per-GPU efficiency (MH/W)
        gpu_power = gpu.get('power_draw', 0)
        gpu['efficiency'] = gpu.get('hashrate', 0) / gpu_power if gpu_power > 0 else 0

        total_power += gpu_power
        total_temp += gpu.get('temperature', 0)
        total_accepted += gpu.get('accepted_shares', 0)
        total_rejected += gpu.get('rejected_shares', 0)
        total_fan += gpu.get('fan_speed', 0)

    data['total_power_draw'] = total_power
    # Rig-wide efficiency
    data['efficiency'] = data.get('total_hashrate', 0) / total_power if total_power > 0 else 0
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
