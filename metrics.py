from prometheus_client import start_http_server, Gauge
import time
import os
import logging
import requests
import database
from miner_api import get_full_miner_data

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
INFO = Gauge('miner_info', 'Miner information', ['miner', 'version', 'worker'])
UPTIME = Gauge('miner_uptime', 'Miner uptime in seconds', ['worker'])
API_UP = Gauge('miner_api_up', 'Whether the miner API is reachable (1) or not (0)', ['worker'])

HASHRATE = Gauge('miner_hashrate', 'Total hashrate in MH/s', ['worker'])
DUAL_HASHRATE = Gauge('miner_dual_hashrate', 'Total dual hashrate in MH/s', ['worker'])
AVG_FAN_SPEED = Gauge('miner_avg_fan_speed', 'Average fan speed of all GPUs in %', ['worker'])
TOTAL_POWER_DRAW = Gauge('miner_total_power_draw', 'Total power draw of all GPUs in W', ['worker'])
TOTAL_SHARES_ACCEPTED = Gauge('miner_total_shares_accepted', 'Total number of accepted shares', ['worker'])
TOTAL_SHARES_REJECTED = Gauge('miner_total_shares_rejected', 'Total number of rejected shares', ['worker'])

GPU_HASHRATE = Gauge('miner_gpu_hashrate', 'Hashrate of a single GPU in MH/s', ['gpu', 'worker'])
GPU_DUAL_HASHRATE = Gauge('miner_gpu_dual_hashrate', 'Dual hashrate of a single GPU in MH/s', ['gpu', 'worker'])
GPU_TEMPERATURE = Gauge('miner_gpu_temperature', 'Temperature of a single GPU in °C', ['gpu', 'worker'])
GPU_POWER_DRAW = Gauge('miner_gpu_power_draw', 'Power draw of a single GPU in W', ['gpu', 'worker'])
GPU_FAN_SPEED = Gauge('miner_gpu_fan_speed', 'Fan speed of a single GPU in %', ['gpu', 'worker'])
GPU_SHARES_ACCEPTED = Gauge('miner_gpu_shares_accepted', 'Number of accepted shares for a single GPU', ['gpu', 'worker'])
GPU_SHARES_REJECTED = Gauge('miner_gpu_shares_rejected', 'Number of rejected shares for a single GPU', ['gpu', 'worker'])

last_prune_time = 0.0

# Telegram configuration
TELEGRAM_ENABLE = os.getenv('TELEGRAM_ENABLE', 'false').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_NOTIFY_THRESHOLD = int(os.getenv('TELEGRAM_NOTIFY_THRESHOLD', 300))

# Notification state
unhealthy_since = None
is_currently_notified = False

def send_telegram_notification(message: str) -> None:
    if not TELEGRAM_ENABLE or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Telegram notification sent successfully")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

def update_metrics() -> None:
    global last_prune_time, unhealthy_since, is_currently_notified
    try:
        data = get_full_miner_data()

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
            if is_currently_notified:
                send_telegram_notification(f"✅ <b>Rig Alert</b>\nStatus: RECOVERED\nHashrate: {data.get('total_hashrate', 0)} MH/s")
                is_currently_notified = False
            unhealthy_since = None

        # Update static info
        INFO.labels(miner=MINER_TYPE, version=MINER_VERSION, worker=WORKER).set(1)

        if not data:
            logger.error("Failed to fetch consolidated miner data")
            API_UP.labels(worker=WORKER).set(0)
            HASHRATE.labels(worker=WORKER).set(0)
            DUAL_HASHRATE.labels(worker=WORKER).set(0)
            AVG_FAN_SPEED.labels(worker=WORKER).set(0)
            TOTAL_POWER_DRAW.labels(worker=WORKER).set(0)
            return

        # Set global metrics from pre-calculated aggregates
        API_UP.labels(worker=WORKER).set(1)
        UPTIME.labels(worker=WORKER).set(data.get('uptime', 0))
        HASHRATE.labels(worker=WORKER).set(data.get('total_hashrate', 0))
        DUAL_HASHRATE.labels(worker=WORKER).set(data.get('total_dual_hashrate', 0))
        AVG_FAN_SPEED.labels(worker=WORKER).set(data.get('avg_fan_speed', 0))
        TOTAL_POWER_DRAW.labels(worker=WORKER).set(data.get('total_power_draw', 0))
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
            GPU_SHARES_ACCEPTED.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('accepted_shares', 0))
            GPU_SHARES_REJECTED.labels(gpu=gpu_idx, worker=WORKER).set(gpu.get('rejected_shares', 0))

        # Log history to SQLite
        database.log_history(
            data.get('total_hashrate', 0),
            data.get('avg_temperature', 0),
            data.get('avg_fan_speed', 0),
            data.get('total_accepted_shares', 0),
            data.get('total_rejected_shares', 0),
            data.get('total_dual_hashrate', 0)
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
        AVG_FAN_SPEED.labels(worker=WORKER).set(0)
        TOTAL_POWER_DRAW.labels(worker=WORKER).set(0)

if __name__ == '__main__':
    database.init_db()
    # Perform an initial update before starting the server to ensure metrics are populated
    update_metrics()
    start_http_server(PORT)
    logger.info(f"Serving Prometheus metrics at port {PORT}")
    while True:
        time.sleep(15)
        update_metrics()
