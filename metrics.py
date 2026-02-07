from prometheus_client import start_http_server, Gauge
import json
import subprocess
import time
import csv
from datetime import datetime
import os
import database
from miner_api import get_gpu_smi_data, get_normalized_miner_data

PORT = 4455

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

last_prune_time = 0

def update_metrics():
    global last_prune_time
    try:
        miner_data = get_normalized_miner_data()
        if not miner_data:
            print("Failed to fetch miner data")
            HASHRATE.set(0)
            DUAL_HASHRATE.set(0)
            AVG_FAN_SPEED.set(0)
            TOTAL_POWER_DRAW.set(0)
            return

        hashrate = miner_data.get('total_hashrate', 0)
        dual_hashrate = miner_data.get('total_dual_hashrate', 0)
        avg_fan_speed = 0
        miner_gpus = miner_data.get('gpus', [])
        num_gpus = len(miner_gpus)

        if num_gpus > 0:
            avg_fan_speed = sum(gpu.get('fan_speed', 0) for gpu in miner_gpus) / num_gpus

        HASHRATE.set(hashrate)
        DUAL_HASHRATE.set(dual_hashrate)
        AVG_FAN_SPEED.set(avg_fan_speed)

        # Get SMI stats
        gpu_stats = get_gpu_smi_data()

        gpus = miner_gpus
        if gpu_stats:
            # Merge SMI stats into miner_gpus
            for i, gpu in enumerate(miner_gpus):
                if i < len(gpu_stats):
                    # Only overwrite if SMI data is non-zero
                    if gpu_stats[i]['temperature'] > 0:
                        gpu['temperature'] = gpu_stats[i]['temperature']
                    if gpu_stats[i]['power_draw'] > 0:
                        gpu['power_draw'] = gpu_stats[i]['power_draw']

        total_power_draw = sum(gpu.get('power_draw', 0) for gpu in gpus)
        TOTAL_POWER_DRAW.set(total_power_draw)

        total_accepted = 0
        total_rejected = 0
        total_temp = 0

        for i, gpu in enumerate(gpus):
            gpu_hashrate = gpu.get('hashrate', 0)
            gpu_dual_hashrate = gpu.get('dual_hashrate', 0)
            gpu_temp = gpu.get('temperature', 0)
            gpu_power = gpu.get('power_draw', 0)
            gpu_fan = gpu.get('fan_speed', 0)
            gpu_accepted = gpu.get('accepted_shares', 0)
            gpu_rejected = gpu.get('rejected_shares', 0)

            GPU_HASHRATE.labels(gpu=str(i)).set(gpu_hashrate)
            GPU_DUAL_HASHRATE.labels(gpu=str(i)).set(gpu_dual_hashrate)
            GPU_TEMPERATURE.labels(gpu=str(i)).set(gpu_temp)
            GPU_POWER_DRAW.labels(gpu=str(i)).set(gpu_power)
            GPU_FAN_SPEED.labels(gpu=str(i)).set(gpu_fan)
            GPU_SHARES_ACCEPTED.labels(gpu=str(i)).set(gpu_accepted)
            GPU_SHARES_REJECTED.labels(gpu=str(i)).set(gpu_rejected)

            total_accepted += gpu_accepted
            total_rejected += gpu_rejected
            total_temp += gpu_temp

        avg_temp = total_temp / num_gpus if num_gpus > 0 else 0

        TOTAL_SHARES_ACCEPTED.set(total_accepted)
        TOTAL_SHARES_REJECTED.set(total_rejected)

        # Log history to SQLite
        database.log_history(hashrate, avg_temp, avg_fan_speed, total_accepted, total_rejected, dual_hashrate)

        # Prune once per hour
        if time.time() - last_prune_time > 3600:
            database.prune_history()
            last_prune_time = time.time()

    except Exception as e:
        print(f"Error updating metrics: {e}")
        HASHRATE.set(0)
        DUAL_HASHRATE.set(0)
        AVG_FAN_SPEED.set(0)
        TOTAL_POWER_DRAW.set(0)

if __name__ == '__main__':
    database.init_db()
    start_http_server(PORT)
    print(f"Serving Prometheus metrics at port {PORT}")
    while True:
        update_metrics()
        time.sleep(15)
