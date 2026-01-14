from prometheus_client import start_http_server, Gauge
import json
import subprocess
import time
import csv
from datetime import datetime

PORT = 4455

# Define Prometheus metrics
HASHRATE = Gauge('lolminer_hashrate', 'Total hashrate in MH/s')
AVG_FAN_SPEED = Gauge('lolminer_avg_fan_speed', 'Average fan speed of all GPUs in %')
TOTAL_POWER_DRAW = Gauge('lolminer_total_power_draw', 'Total power draw of all GPUs in W')

GPU_HASHRATE = Gauge('lolminer_gpu_hashrate', 'Hashrate of a single GPU in MH/s', ['gpu'])
GPU_TEMPERATURE = Gauge('lolminer_gpu_temperature', 'Temperature of a single GPU in °C', ['gpu'])
GPU_POWER_DRAW = Gauge('lolminer_gpu_power_draw', 'Power draw of a single GPU in W', ['gpu'])
GPU_FAN_SPEED = Gauge('lolminer_gpu_fan_speed', 'Fan speed of a single GPU in %', ['gpu'])
GPU_SHARES_ACCEPTED = Gauge('lolminer_gpu_shares_accepted', 'Number of accepted shares for a single GPU', ['gpu'])
GPU_SHARES_REJECTED = Gauge('lolminer_gpu_shares_rejected', 'Number of rejected shares for a single GPU', ['gpu'])

def update_metrics():
    try:
        # Get lolMiner API data
        api_data_raw = subprocess.check_output(['curl', '-s', 'http://localhost:4444/'])
        api_data = json.loads(api_data_raw)

        hashrate = api_data.get('Total_Performance', [0])[0]
        gpus_data = api_data.get('GPUs', [])
        num_gpus = len(gpus_data)

        if num_gpus > 0:
            avg_fan_speed = sum(gpu.get('Fan_Speed', 0) for gpu in gpus_data) / num_gpus
        else:
            avg_fan_speed = 0

        HASHRATE.set(hashrate)

        # Log hashrate to CSV
        with open('hashrate_history.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), hashrate])

        AVG_FAN_SPEED.set(avg_fan_speed)

        lolminer_gpus = [{'hashrate': gpu.get('Performance'), 'fan_speed': gpu.get('Fan_Speed'), 'shares_accepted': gpu.get('Accepted_Shares'), 'shares_rejected': gpu.get('Rejected_Shares')} for gpu in gpus_data]

        # Get nvidia-smi stats
        smi_output = ""
        smi_cmd = ""
        gpu_stats = []

        # Get nvidia-smi or rocm-smi stats if available
        smi_output = ""
        smi_cmd = ""
        gpu_stats = []
        is_nvidia = False

        # Detect GPU type
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
                # No SMI tool found
                smi_cmd = ""

        if smi_cmd:
            try:
                smi_output = subprocess.check_output(smi_cmd, shell=True, stderr=subprocess.DEVNULL).decode()
                for i, line in enumerate(smi_output.strip().split('\n')):
                    try:
                        if is_nvidia:
                            temp, power = map(float, line.split(', '))
                            gpu_stats.append({'temperature': temp, 'power_draw': power})
                        else: # AMD
                            parts = line.split(',')
                            temp = float(parts[1])
                            power = float(parts[2].replace('W', '').strip())
                            gpu_stats.append({'temperature': temp, 'power_draw': power})
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing SMI data for GPU {i}: {e}")
                        gpu_stats.append({'temperature': 0, 'power_draw': 0})

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"Error executing SMI command: {e}")
                pass

        gpus = lolminer_gpus
        if gpu_stats:
            gpus = [dict(lol, **stats) for lol, stats in zip(lolminer_gpus, gpu_stats)]

        total_power_draw = sum(gpu.get('power_draw', 0) for gpu in gpus)
        TOTAL_POWER_DRAW.set(total_power_draw)

        for i, gpu in enumerate(gpus):
            GPU_HASHRATE.labels(gpu=i).set(gpu.get('hashrate', 0))
            GPU_TEMPERATURE.labels(gpu=i).set(gpu.get('temperature', 0))
            GPU_POWER_DRAW.labels(gpu=i).set(gpu.get('power_draw', 0))
            GPU_FAN_SPEED.labels(gpu=i).set(gpu.get('fan_speed', 0))
            GPU_SHARES_ACCEPTED.labels(gpu=i).set(gpu.get('shares_accepted', 0))
            GPU_SHARES_REJECTED.labels(gpu=i).set(gpu.get('shares_rejected', 0))

    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
        HASHRATE.set(0)
        AVG_FAN_SPEED.set(0)
        TOTAL_POWER_DRAW.set(0)

if __name__ == '__main__':
    start_http_server(PORT)
    print(f"Serving Prometheus metrics at port {PORT}")
    while True:
        update_metrics()
        time.sleep(15)
