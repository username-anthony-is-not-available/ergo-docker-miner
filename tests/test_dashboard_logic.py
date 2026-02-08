import unittest
from unittest.mock import patch, MagicMock
import os
import json
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
import dashboard
import asyncio

class TestDashboardLogic(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(dashboard.app)

    @patch('dashboard.get_full_miner_data')
    def test_background_task_update(self, mock_full_data):
        # Mock consolidated miner data
        mock_full_data.return_value = {
            'miner': 'lolminer',
            'status': 'Mining',
            'uptime': 1000,
            'total_hashrate': 120.5,
            'total_dual_hashrate': 0,
            'total_power_draw': 100.0,
            'avg_temperature': 50.0,
            'gpus': [
                {
                    'index': 0,
                    'hashrate': 60.2,
                    'temperature': 50.0,
                    'power_draw': 100.0,
                    'fan_speed': 50
                }
            ]
        }

        with patch('dashboard.sio.emit') as mock_emit:
            # Mock sleep to break the infinite loop after one iteration
            with patch('asyncio.sleep', side_effect=asyncio.CancelledError):
                try:
                    asyncio.run(dashboard.background_task())
                except asyncio.CancelledError:
                    pass

            self.assertTrue(mock_emit.called)
            args, _ = mock_emit.call_args
            self.assertEqual(args[0], 'update')
            data = args[1]
            self.assertEqual(data['status'], 'Mining')
            self.assertEqual(data['total_power_draw'], 100.0)
            self.assertEqual(data['avg_temperature'], 50.0)

    @patch('dashboard.get_gpu_names')
    def test_api_gpu_models(self, mock_get_names):
        mock_get_names.return_value = ['RTX 3070']
        response = self.client.get('/api/gpu-models')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['models'], ['RTX 3070'])

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    @patch('dashboard.read_env_file')
    def test_api_config_get(self, mock_read):
        mock_read.return_value = {'WALLET_ADDRESS': 'test_wallet'}
        response = self.client.get('/api/config')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['WALLET_ADDRESS'], 'test_wallet')

    @patch('os.path.exists')
    def test_api_logs_download(self, mock_exists):
        mock_exists.return_value = True
        with patch('dashboard.FileResponse', return_value=JSONResponse({"mock": "file"})) as mock_file:
            response = self.client.get('/api/logs/download')
            self.assertEqual(response.status_code, 200)
            mock_file.assert_called_once()

    def test_gpu_history(self):
        with patch('database.get_gpu_history', return_value=[]) as mock_get:
            response = self.client.get('/gpu-history/0')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            mock_get.assert_called_once_with(gpu_index=0)

if __name__ == '__main__':
    unittest.main()
