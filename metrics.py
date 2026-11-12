from prometheus_client import start_http_server, Gauge
import json
import logging
import os
import socket
import time
from urllib.parse import urlsplit
import requests
import database
from miner_api import get_full_miner_data, get_node_status, get_services_status
import discord_notifier
from env_config import get_secret

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics")

PORT = int(os.getenv('METRICS_PORT', 4455))
WORKER = os.getenv('WORKER_NAME', 'ergo-miner')
MINER_TYPE = os.getenv('MINER', 'lolminer')
MINER_VERSION = os.getenv('LOLMINER_VERSION' if MINER_TYPE == 'lolminer' else 'T_REX_VERSION', 'unknown')

# Define Prometheus metrics (generic)
INFO = Gauge('miner_info', 'Miner information', ['miner', 'version', 'worker', 'driver'])
UPTIME = Gauge('miner_uptime', 'Miner uptime in seconds', ['worker'])
API_UP = Gauge('miner_api_up', 'Whether the miner API is reachable (1) or not (0)', ['worker'])
MINER_INSTANCE_UP = Gauge('miner_instance_up', 'Whether a specific miner instance is UP (1) or DOWN (0)', ['port', 'worker'])
GPU_COUNT = Gauge('miner_gpu_count', 'Number of GPUs detected by the miner', ['worker'])
NODE_SYNCED = Gauge('miner_node_synced', 'Whether the Ergo node is synced (1) or not (0)', ['worker'])

HASHRATE = Gauge('miner_hashrate', 'Total hashrate in MH/s', ['worker'])
DUAL_HASHRATE = Gauge('miner_dual_hashrate', 'Total dual hashrate in MH/s', ['worker'])
AVG_TEMPERATURE = Gauge('miner_avg_temperature', 'Average temperature of all GPUs in °C', ['worker'])
MAX_GPU_TEMPERATURE = Gauge('miner_max_gpu_temperature', 'Maximum GPU temperature across all GPUs in °C', ['worker'])
AVG_FAN_SPEED = Gauge('miner_avg_fan_speed', 'Average fan speed of all GPUs in %', ['worker'])
TOTAL_POWER_DRAW = Gauge('miner_total_power_draw', 'Total power draw of all GPUs in W', ['worker'])
AVG_POWER_DRAW = Gauge('miner_avg_power_draw', 'Average power draw per GPU in W', ['worker'])
EFFICIENCY = Gauge('miner_efficiency', 'Rig-wide power efficiency in MH/s per Watt', ['worker'])
TOTAL_SHARES_ACCEPTED = Gauge('miner_total_shares_accepted', 'Total number of accepted shares', ['worker'])
TOTAL_SHARES_REJECTED = Gauge('miner_total_shares_rejected', 'Total number of rejected shares', ['worker'])
API_LATENCY = Gauge('miner_api_latency_seconds', 'Latency of miner API data collection in seconds', ['worker'])
NODE_LATENCY = Gauge('miner_node_latency_seconds', 'Latency of Ergo node status check in seconds', ['worker'])
POOL_LATENCY = Gauge('miner_pool_latency_seconds', 'TCP connection latency to the configured mining pool in seconds', ['pool', 'worker'])
POOL_UP = Gauge('miner_pool_up', 'Whether the configured mining pool TCP endpoint is reachable (1) or not (0)', ['pool', 'worker'])

SERVICE_STATUS = Gauge('miner_service_status', 'Status of background services (1=Running, 0=Stopped/Disabled)', ['service', 'worker'])

GPU_HASHRATE = Gauge('miner_gpu_hashrate', 'Hashrate of a single GPU in MH/s', ['gpu', 'worker'])
GPU_DUAL_HASHRATE = Gauge('miner_gpu_dual_hashrate', 'Dual hashrate of a single GPU in MH/s', ['gpu', 'worker'])
GPU_TEMPERATURE = Gauge('miner_gpu_temperature', 'Temperature of a single GPU in °C', ['gpu', 'worker'])
GPU_POWER_DRAW = Gauge('miner_gpu_power_draw', 'Power draw of a single GPU in W', ['gpu', 'worker'])
GPU_FAN_SPEED = Gauge('miner_gpu_fan_speed', 'Fan speed of a single GPU in %', ['gpu', 'worker'])
GPU_EFFICIENCY = Gauge('miner_gpu_efficiency', 'Power efficiency of a single GPU in MH/s per Watt', ['gpu', 'worker'])
GPU_SHARES_ACCEPTED = Gauge('miner_gpu_shares_accepted', 'Number of accepted shares for a single GPU', ['gpu', 'worker'])
GPU_SHARES_REJECTED = Gauge('miner_gpu_shares_rejected', 'Number of rejected shares for a single GPU', ['gpu', 'worker'])

last_prune_time = 0.0

# Telegram configuration
TELEGRAM_ENABLE = os.getenv('TELEGRAM_ENABLE', 'false').lower() == 'true'
TELEGRAM_BOT_TOKEN = get_secret('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = get_secret('TELEGRAM_CHAT_ID')
TELEGRAM_NOTIFY_THRESHOLD = int(os.getenv('TELEGRAM_NOTIFY_THRESHOLD', 300))

# Notification state
unhealthy_since = None
is_currently_notified = False

# Discord temperature alert state
discord_temp_unhealthy_since = None
discord_temp_is_notified = False
discord_temp_gpu_index = None

def send_telegram_notification(message: str) -> None:
    """Send a Telegram notification without exposing bot tokens in logs."""
    bot_token = TELEGRAM_BOT_TOKEN or get_secret('TELEGRAM_BOT_TOKEN')
    chat_id = TELEGRAM_CHAT_ID or get_secret('TELEGRAM_CHAT_ID')
    if not TELEGRAM_ENABLE or not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram notification sent successfully")
    except Exception as e:
        safe_err = str(e).replace(bot_token, "<redacted-bot-token>")
        logger.error(f"Failed to send Telegram notification: {safe_err}")

def measure_pool_latency(pool_address: str, timeout: float = 2.0) -> float | None:
    """Measure TCP handshake latency in seconds to a stratum mining pool."""
    if not pool_address or not pool_address.strip():
        return None
    try:
        parsed = urlsplit(pool_address.strip())
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None

    if not host or port is None:
        return None

    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return max(time.perf_counter() - start, 0.0)
    except OSError as e:
        logger.debug(f"Pool latency probe failed for {host}:{port}: {e}")
        return None


def _update_network_latency_metrics(api_latency: float, node_latency: float) -> None:
    """Record miner API, node, and pool latency gauges."""
    API_LATENCY.labels(worker=WORKER).set(api_latency)
    NODE_LATENCY.labels(worker=WORKER).set(node_latency)

    pool_address = os.getenv('POOL_ADDRESS', '').strip()
    if pool_address:
        latency = measure_pool_latency(pool_address)
        if latency is not None:
            POOL_UP.labels(pool=pool_address, worker=WORKER).set(1)
            POOL_LATENCY.labels(pool=pool_address, worker=WORKER).set(latency)
        else:
            POOL_UP.labels(pool=pool_address, worker=WORKER).set(0)


def update_metrics() -> None:
    global last_prune_time, unhealthy_since, is_currently_notified
    global discord_temp_unhealthy_since, discord_temp_is_notified, discord_temp_gpu_index
    try:
        api_start = time.perf_counter()
        data = get_full_miner_data()
        api_latency = max(time.perf_counter() - api_start, 0.0)

        node_start = time.perf_counter()
        node_status = get_node_status()
        node_latency = max(time.perf_counter() - node_start, 0.0)

        _update_network_latency_metrics(api_latency, node_latency)

        # Update node sync metric
        NODE_SYNCED.labels(worker=WORKER).set(1 if node_status.get('is_synced') else 0)

        # Update service status metrics
        services = get_services_status()
        for service, s_info in services.items():
            val = 1 if s_info['status'] == 'Running' else 0
            SERVICE_STATUS.labels(service=service, worker=WORKER).set(val)

        # Telegram health check logic
        is_unhealthy = (data is None) or (data.get('total_hashrate', 0) == 0)
        if is_unhealthy:
            if unhealthy_since is None:
                unhealthy_since = time.time()
            elapsed = time.time() - unhealthy_since
            if elapsed >= TELEGRAM_NOTIFY_THRESHOLD and not is_currently_notified:
                reason = "API Unreachable" if data is None else "Zero Hashrate"
                send_telegram_notification(f"⚠️ <b>Rig Alert</b>\nStatus: DOWN\nReason: {reason}\nDuration: {int(elapsed)}s")
                is_currently_notified = True
        else:
            if data is not None and is_currently_notified:
                send_telegram_notification(f"✅ <b>Rig Alert</b>\nStatus: RECOVERED\nHashrate: {data.get('total_hashrate', 0)} MH/s")
                is_currently_notified = False
            unhealthy_since = None

        # Extract driver version if available
        driver_version = data.get('driver_version', 'unknown') if data else 'unknown'
        if driver_version != 'unknown':
            logger.info(f"Detected GPU Driver version: {driver_version}")

        # Update static info
        INFO.labels(miner=MINER_TYPE, version=MINER_VERSION, worker=WORKER, driver=driver_version).set(1)

        if not data:
            logger.error("Failed to fetch consolidated miner data")
            API_UP.labels(worker=WORKER).set(0)
            GPU_COUNT.labels(worker=WORKER).set(0)
            HASHRATE.labels(worker=WORKER).set(0)
            DUAL_HASHRATE.labels(worker=WORKER).set(0)
            AVG_TEMPERATURE.labels(worker=WORKER).set(0)
            MAX_GPU_TEMPERATURE.labels(worker=WORKER).set(0)
            AVG_FAN_SPEED.labels(worker=WORKER).set(0)
            TOTAL_POWER_DRAW.labels(worker=WORKER).set(0)
            AVG_POWER_DRAW.labels(worker=WORKER).set(0)
            return

        # Set global metrics from pre-calculated aggregates
        API_UP.labels(worker=WORKER).set(1)

        # Update individual miner instance status
        instances = data.get('miner_instances', {})
        for port, status in instances.items():
            val = 1 if status == 'UP' else 0
            MINER_INSTANCE_UP.labels(port=str(port), worker=WORKER).set(val)

        gpus = data.get('gpus', [])
        gpu_count = len(gpus)
        max_temp = max((gpu.get('temperature', 0) for gpu in gpus), default=0)
        avg_power = data.get('total_power_draw', 0) / gpu_count if gpu_count > 0 else 0

        GPU_COUNT.labels(worker=WORKER).set(gpu_count)
        UPTIME.labels(worker=WORKER).set(data.get('uptime', 0))
        HASHRATE.labels(worker=WORKER).set(data.get('total_hashrate', 0))
        DUAL_HASHRATE.labels(worker=WORKER).set(data.get('total_dual_hashrate', 0))
        AVG_TEMPERATURE.labels(worker=WORKER).set(data.get('avg_temperature', 0))
        MAX_GPU_TEMPERATURE.labels(worker=WORKER).set(max_temp)
        AVG_FAN_SPEED.labels(worker=WORKER).set(data.get('avg_fan_speed', 0))
        TOTAL_POWER_DRAW.labels(worker=WORKER).set(data.get('total_power_draw', 0))
        AVG_POWER_DRAW.labels(worker=WORKER).set(avg_power)
        EFFICIENCY.labels(worker=WORKER).set(data.get('efficiency', 0))
        TOTAL_SHARES_ACCEPTED.labels(worker=WORKER).set(data.get('total_accepted_shares', 0))
        TOTAL_SHARES_REJECTED.labels(worker=WORKER).set(data.get('total_rejected_shares', 0))

        # Set per-GPU metrics
        for i, gpu in enumerate(data.get('gpus', [])):
            gpu_idx = str(gpu.get('index', i))

            GPU_HASHRATE.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('hashrate', 0))
            GPU_DUAL_HASHRATE.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('dual_hashrate', 0))
            GPU_TEMPERATURE.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('temperature', 0))
            GPU_POWER_DRAW.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('power_draw', 0))
            GPU_FAN_SPEED.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('fan_speed', 0))
            GPU_EFFICIENCY.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('efficiency', 0))
            GPU_SHARES_ACCEPTED.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('accepted_shares', 0))
            GPU_SHARES_REJECTED.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('rejected_shares', 0))

        # Check GPU temperature thresholds and send Discord alerts
        try:
            gpu_profile = os.getenv('GPU_PROFILE')
            if gpu_profile:
                with open('gpu_profiles.json', 'r') as f:
                    profiles = json.load(f)
                profile_settings = profiles.get(gpu_profile, {})
                temp_threshold = profile_settings.get('GPU_TEMP_THRESHOLD', 80)
            else:
                temp_threshold = 80

            gpus_over_temp = []
            for gpu in data.get('gpus', []):
                gpu_idx = gpu.get('index', 'unknown')
                temp = gpu.get('temperature', 0)
                if temp > temp_threshold:
                    gpus_over_temp.append((gpu_idx, temp))

            if gpus_over_temp:
                if discord_temp_unhealthy_since is None:
                    discord_temp_unhealthy_since = time.time()
                    discord_temp_gpu_index = [x[0] for x in gpus_over_temp]
                elapsed = time.time() - discord_temp_unhealthy_since
                if elapsed >= discord_notifier.DISCORD_NOTIFY_THRESHOLD and not discord_temp_is_notified:
                    gpu_list = ', '.join([f"GPU {x[0]} ({x[1]}°C)" for x in gpus_over_temp])
                    msg = f"⚠️ **GPU Temperature Alert**\nThreshold: {temp_threshold}°C\nOver limit: {gpu_list}"
                    discord_notifier.send_discord_notification(msg)
                    discord_temp_is_notified = True
            else:
                if discord_temp_is_notified:
                    discord_notifier.send_discord_notification(f"✅ **GPU Temperature Recovered**\nAll GPUs below {temp_threshold}°C")
                    discord_temp_is_notified = False
                discord_temp_unhealthy_since = None
                discord_temp_gpu_index = None
        except Exception as e:
            logger.error(f"Error checking GPU temperature thresholds: {e}")

        # Log history to SQLite
        database.log_history(
            data.get('total_hashrate', 0),
            data.get('avg_temperature', 0),
            data.get('avg_fan_speed', 0),
            data.get('total_accepted_shares', 0),
            data.get('total_rejected_shares', 0),
            data.get('total_dual_hashrate', 0),
            data.get('total_power_draw', 0),
            data.get('gpus', [])
        )

        # Prune once per hour
        if time.time() - last_prune_time > 3600:
            database.prune_history()
            last_prune_time = time.time()
            logger.info("History database pruned")

    except Exception as e:
        logger.exception(f"Error updating metrics: {e}")
        API_UP.labels(worker=WORKER).set(0)
        HASHRATE.labels(worker=WORKER).set(0)
        DUAL_HASHRATE.labels(worker=WORKER).set(0)
        AVG_TEMPERATURE.labels(worker=WORKER).set(0)
        MAX_GPU_TEMPERATURE.labels(worker=WORKER).set(0)
        AVG_FAN_SPEED.labels(worker=WORKER).set(0)
        TOTAL_POWER_DRAW.labels(worker=WORKER).set(0)
        AVG_POWER_DRAW.labels(worker=WORKER).set(0)

if __name__ == '__main__':
    database.init_db()
    # Perform an initial update before starting the server to ensure metrics are populated
    update_metrics()
    start_http_server(PORT)
    logger.info(f"Serving Prometheus metrics at port {PORT}")
    while True:
        time.sleep(15)
        update_metrics()
