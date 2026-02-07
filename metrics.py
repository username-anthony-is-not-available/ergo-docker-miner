from prometheus_client import start_http_server, Gauge
import time
import os
import logging
import database
from miner_api import get_full_miner_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("metrics")

PORT = int(os.getenv('METRICS_PORT', 4455))

# Define Prometheus metrics (generic)
HASHRATE = Gauge('miner_hashrate', 'Total hashrate in MH/s')
DUAL_HASHRATE = Gauge('miner_dual_hashrate', 'Total dual hashrate in MH/s')
AVG_FAN_SPEED = Gauge('miner_avg_fan_speed', 'Average fan speed of all GPUs in %')
TOTAL_POWER_DRAW = Gauge('miner_total_power_draw', 'Total power draw of all GPUs in W')
TOTAL_SHARES_ACCEPTED = Gauge('miner_total_shares_accepted', 'Total number of accepted shares')
TOTAL_SHARES_REJECTED = Gauge('miner_total_shares_rejected', 'Total number of rejected shares')

GPU_HASHRATE = Gauge('miner_gpu_hashrate', 'Hashrate of a single GPU in MH/s', ['gpu'])
GPU_DUAL_HASHRATE = Gauge('miner_gpu_dual_hashrate', 'Dual hashrate of a single GPU in MH/s', ['gpu'])
GPU_TEMPERATURE = Gauge('miner_gpu_temperature', 'Temperature of a single GPU in °C', ['gpu'])
GPU_POWER_DRAW = Gauge('miner_gpu_power_draw', 'Power draw of a single GPU in W', ['gpu'])
GPU_FAN_SPEED = Gauge('miner_gpu_fan_speed', 'Fan speed of a single GPU in %', ['gpu'])
GPU_SHARES_ACCEPTED = Gauge('miner_gpu_shares_accepted', 'Number of accepted shares for a single GPU', ['gpu'])
GPU_SHARES_REJECTED = Gauge('miner_gpu_shares_rejected', 'Number of rejected shares for a single GPU', ['gpu'])

last_prune_time = 0.0

def update_metrics() -> None:
    global last_prune_time
    try:
        data = get_full_miner_data()
        if not data:
            logger.error("Failed to fetch consolidated miner data")
            HASHRATE.set(0)
            DUAL_HASHRATE.set(0)
            AVG_FAN_SPEED.set(0)
            TOTAL_POWER_DRAW.set(0)
            return

        # Set global metrics from pre-calculated aggregates
        HASHRATE.set(data.get('total_hashrate', 0))
        DUAL_HASHRATE.set(data.get('total_dual_hashrate', 0))
        AVG_FAN_SPEED.set(data.get('avg_fan_speed', 0))
        TOTAL_POWER_DRAW.set(data.get('total_power_draw', 0))
        TOTAL_SHARES_ACCEPTED.set(data.get('total_accepted_shares', 0))
        TOTAL_SHARES_REJECTED.set(data.get('total_rejected_shares', 0))

        # Set per-GPU metrics
        for i, gpu in enumerate(data.get('gpus', [])):
            gpu_idx = str(gpu.get('index', i))

            GPU_HASHRATE.labels(gpu=gpu_idx).set(gpu.get('hashrate', 0))
            GPU_DUAL_HASHRATE.labels(gpu=gpu_idx).set(gpu.get('dual_hashrate', 0))
            GPU_TEMPERATURE.labels(gpu=gpu_idx).set(gpu.get('temperature', 0))
            GPU_POWER_DRAW.labels(gpu=gpu_idx).set(gpu.get('power_draw', 0))
            GPU_FAN_SPEED.labels(gpu=gpu_idx).set(gpu.get('fan_speed', 0))
            GPU_SHARES_ACCEPTED.labels(gpu=gpu_idx).set(gpu.get('accepted_shares', 0))
            GPU_SHARES_REJECTED.labels(gpu=gpu_idx).set(gpu.get('rejected_shares', 0))

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
        HASHRATE.set(0)
        DUAL_HASHRATE.set(0)
        AVG_FAN_SPEED.set(0)
        TOTAL_POWER_DRAW.set(0)

if __name__ == '__main__':
    database.init_db()
    start_http_server(PORT)
    logger.info(f"Serving Prometheus metrics at port {PORT}")
    while True:
        update_metrics()
        time.sleep(15)
