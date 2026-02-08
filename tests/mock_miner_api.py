import http.server
import json
import os
import signal
import sys
from urllib.parse import urlparse, parse_qs

class MockMinerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # We read state from a file so it can be changed without restarting the server
        state_file = os.getenv('MOCK_STATE_FILE', '/tmp/mock_miner_state.json')
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
        else:
            state = {
                'hashrate': float(os.getenv('MOCK_HASHRATE', 100.0)),
                'accepted': int(os.getenv('MOCK_ACCEPTED', 100)),
                'rejected': int(os.getenv('MOCK_REJECTED', 0)),
                'uptime': int(os.getenv('MOCK_UPTIME', 3600))
            }

        miner_type = os.getenv('MINER', 'lolminer')

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        if miner_type == 'lolminer':
            response = {
                'Session': {
                    'Uptime': state['uptime'],
                    'Algorithm': 'Autolykos2',
                    'Driver': '535.129.03'
                },
                'Total_Performance': [state['hashrate'], 0.0],
                'GPUs': [
                    {
                        'Index': 0,
                        'Name': 'Mock RTX 3080',
                        'Performance': [state['hashrate'], 0.0],
                        'Fan_Speed': 50,
                        'Accepted_Shares': state['accepted'],
                        'Rejected_Shares': state['rejected']
                    }
                ]
            }
        elif miner_type == 't-rex':
            response = {
                'uptime': state['uptime'],
                'hashrate': state['hashrate'] * 1000000,
                'gpus': [
                    {
                        'index': 0,
                        'name': 'Mock RTX 3080',
                        'hashrate': state['hashrate'] * 1000000,
                        'fan_speed': 50,
                        'temperature': 60,
                        'power': 200,
                        'shares': {
                            'accepted_count': state['accepted'],
                            'rejected_count': state['rejected']
                        }
                    }
                ]
            }
        else:
            response = {"error": "Unknown miner type"}

        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        return

def run_server(port):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, MockMinerHandler)
    print(f"Mock Miner API serving on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 4444))
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0))

    run_server(port)
