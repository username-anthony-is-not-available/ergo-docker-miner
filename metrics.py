import http.server
import socketserver
import json
import subprocess

PORT = 4455

class MetricsHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        metrics = self.get_metrics()
        self.wfile.write(json.dumps(metrics).encode())

    def get_metrics(self):
        try:
            # Check if lolMiner API is available
            api_data = subprocess.check_output(['curl', '-s', 'http://localhost:4444/'])
            metrics = json.loads(api_data)

            hashrate = metrics.get('Total_Performance', [None])[0]
            gpus_data = metrics.get('GPUs', [])
            num_gpus = len(gpus_data)

            if num_gpus > 0:
                avg_fan_speed = sum(gpu.get('Fan_Speed', 0) for gpu in gpus_data) / num_gpus
            else:
                avg_fan_speed = 0

            lolminer_gpus = [{'hashrate': gpu.get('Performance')} for gpu in gpus_data]

            # Get nvidia-smi stats
            try:
                nvidia_stats_raw = subprocess.check_output(['nvidia-smi', '--query-gpu=temperature.gpu,power.draw', '--format=csv,noheader,nounits']).decode()
                nvidia_stats = []
                for line in nvidia_stats_raw.strip().split('\n'):
                    temp, power = line.split(', ')
                    nvidia_stats.append({'temperature': float(temp), 'power_draw': float(power)})

                # Merge stats
                gpus = [dict(lol, **nvidia) for lol, nvidia in zip(lolminer_gpus, nvidia_stats)]

                if num_gpus > 0:
                    avg_temperature = sum(gpu.get('temperature', 0) for gpu in gpus) / num_gpus
                else:
                    avg_temperature = 0
                total_power_draw = sum(gpu.get('power_draw', 0) for gpu in gpus)

            except (subprocess.CalledProcessError, FileNotFoundError):
                gpus = [dict(gpu, temperature='N/A', power_draw='N/A') for gpu in lolminer_gpus]
                avg_temperature = 'N/A'
                total_power_draw = 'N/A'

            return {
                'hashrate': hashrate,
                'avg_temperature': avg_temperature,
                'avg_fan_speed': avg_fan_speed,
                'total_power_draw': total_power_draw,
                'gpus': gpus
            }

        except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
            return {
                'hashrate': 'N/A',
                'avg_temperature': 'N/A',
                'avg_fan_speed': 'N/A',
                'total_power_draw': 'N/A',
                'gpus': []
            }

with socketserver.TCPServer(("", PORT), MetricsHandler) as httpd:
    print(f"Serving at port {PORT}")
    httpd.serve_forever()
