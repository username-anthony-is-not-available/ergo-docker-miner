import unittest
from unittest.mock import patch, MagicMock
import os
import json
import dashboard

class TestDashboardLogic(unittest.TestCase):

    def setUp(self):
        dashboard.app.testing = True
        self.client = dashboard.app.test_client()

    @patch('dashboard.get_normalized_miner_data')
    def test_background_thread_update(self, mock_miner_data):
        # Mock normalized miner data
        mock_miner_data.return_value = {
            'miner': 'lolminer',
            'uptime': 1000,
            'total_hashrate': 120.5,
            'total_dual_hashrate': 0,
            'gpus': [
                {
                    'index': 0,
                    'hashrate': 60.2,
                    'dual_hashrate': 0,
                    'fan_speed': 50,
                    'accepted_shares': 10,
                    'rejected_shares': 1,
                    'temperature': 0,
                    'power_draw': 0
                }
            ]
        }

        with patch('dashboard.get_gpu_smi_data') as mock_smi:
            mock_smi.return_value = [{'temperature': 50, 'power_draw': 100}]
            with patch('dashboard.socketio.emit') as mock_emit:
                # We can't easily run the actual background thread in a unit test,
                # but we can test the logic inside it by calling it once.
                # Since background_thread is an infinite loop, we'll mock the sleep to break after one iteration.
                with patch('time.sleep', side_effect=InterruptedError):
                    try:
                        dashboard.background_thread()
                    except InterruptedError:
                        pass

                self.assertTrue(mock_emit.called)
                args, kwargs = mock_emit.call_args
                self.assertEqual(args[0], 'update')
                data = args[1]
                self.assertEqual(data['status'], 'Mining')
                self.assertEqual(data['total_power_draw'], 100)
                self.assertEqual(data['avg_temperature'], 50)

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_config_route(self):
        response = self.client.get('/config')
        self.assertEqual(response.status_code, 200)

    @patch('dashboard.read_env_file')
    def test_api_config_get(self, mock_read):
        mock_read.return_value = {'WALLET_ADDRESS': 'test_wallet'}
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['WALLET_ADDRESS'], 'test_wallet')

if __name__ == '__main__':
    unittest.main()
