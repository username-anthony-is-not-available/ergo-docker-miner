import unittest
from unittest.mock import patch, MagicMock
import os
import subprocess
import requests
import miner_api

class TestMinerApi(unittest.TestCase):

    @patch('requests.get')
    def test_get_normalized_miner_data_lolminer(self, mock_get):
        # Mock lolMiner API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'Session': {'Uptime': 1000},
            'Total_Performance': [120.5, 250.0],
            'GPUs': [
                {
                    'Performance': [60.2, 125.0],
                    'Fan_Speed': 50,
                    'Accepted_Shares': 10,
                    'Rejected_Shares': 1
                }
            ]
        }
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {'MINER': 'lolminer'}):
            data = miner_api.get_normalized_miner_data()
            self.assertEqual(data['miner'], 'lolminer')
            self.assertEqual(data['total_hashrate'], 120.5)
            self.assertEqual(data['total_dual_hashrate'], 250.0)
            self.assertEqual(len(data['gpus']), 1)
            self.assertEqual(data['gpus'][0]['hashrate'], 60.2)
            self.assertEqual(data['gpus'][0]['dual_hashrate'], 125.0)

    @patch('requests.get')
    def test_get_normalized_miner_data_trex(self, mock_get):
        # Mock T-Rex API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'uptime': 2000,
            'hashrate': 120000000,
            'gpus': [
                {
                    'hashrate': 60000000,
                    'fan_speed': 60,
                    'temperature': 55,
                    'power': 150,
                    'shares': {'accepted_count': 20, 'rejected_count': 2}
                }
            ]
        }
        mock_get.return_value = mock_response

        with patch.dict(os.environ, {'MINER': 't-rex'}):
            data = miner_api.get_normalized_miner_data()
            self.assertEqual(data['miner'], 't-rex')
            self.assertEqual(data['total_hashrate'], 120.0)
            self.assertEqual(data['gpus'][0]['temperature'], 55)
            self.assertEqual(data['gpus'][0]['power_draw'], 150)

    @patch('requests.get')
    def test_get_normalized_miner_data_retry(self, mock_get):
        # Mock failure then success
        mock_get.side_effect = [
            requests.exceptions.RequestException("API Down"),
            MagicMock(json=lambda: {'Session': {'Uptime': 1000}, 'Total_Performance': [100.0], 'GPUs': []})
        ]

        with patch.dict(os.environ, {'MINER': 'lolminer'}):
            data = miner_api.get_normalized_miner_data()
            self.assertIsNotNone(data)
            self.assertEqual(data['total_hashrate'], 100.0)
            self.assertEqual(mock_get.call_count, 2)

    @patch('subprocess.check_output')
    def test_get_gpu_smi_data_nvidia(self, mock_check_output):
        def side_effect(cmd, *args, **kwargs):
            if cmd == ['which', 'nvidia-smi']:
                return b'/usr/bin/nvidia-smi'
            if 'nvidia-smi --query-gpu' in cmd:
                return b'60, 120, 50\n65, 130, 55'
            raise subprocess.CalledProcessError(1, cmd)

        mock_check_output.side_effect = side_effect

        data = miner_api.get_gpu_smi_data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['temperature'], 60.0)
        self.assertEqual(data[0]['power_draw'], 120.0)
        self.assertEqual(data[0]['fan_speed'], 50.0)

    @patch('psutil.process_iter')
    def test_get_services_status(self, mock_iter):
        mock_proc1 = MagicMock()
        mock_proc1.info = {'cmdline': ['python3', 'metrics.py']}
        mock_proc2 = MagicMock()
        mock_proc2.info = {'cmdline': ['/bin/bash', './cuda_monitor.sh']}
        mock_iter.return_value = [mock_proc1, mock_proc2]

        with patch.dict(os.environ, {'AUTO_RESTART_ON_CUDA_ERROR': 'true'}):
            status = miner_api.get_services_status()
            self.assertEqual(status['metrics.py'], 'Running')
            self.assertEqual(status['cuda_monitor.sh'], 'Running')
            self.assertEqual(status['profit_switcher.py'], 'Stopped')

        with patch.dict(os.environ, {'AUTO_RESTART_ON_CUDA_ERROR': 'false'}):
            status = miner_api.get_services_status()
            self.assertEqual(status['cuda_monitor.sh'], 'Disabled')

    @patch('subprocess.check_output')
    def test_get_gpu_names_nvidia(self, mock_check_output):
        def side_effect(cmd, *args, **kwargs):
            if cmd == ['which', 'nvidia-smi']:
                return b'/usr/bin/nvidia-smi'
            if cmd == ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader']:
                return b'NVIDIA GeForce RTX 3070\nNVIDIA GeForce RTX 3080'
            raise subprocess.CalledProcessError(1, cmd)

        mock_check_output.side_effect = side_effect

        names = miner_api.get_gpu_names()
        self.assertEqual(names, ['NVIDIA GeForce RTX 3070', 'NVIDIA GeForce RTX 3080'])

    @patch('miner_api.get_normalized_miner_data')
    @patch('miner_api.get_gpu_smi_data')
    def test_get_full_miner_data(self, mock_smi, mock_normalized):
        mock_normalized.return_value = {
            'miner': 'lolminer',
            'total_hashrate': 120.0,
            'total_dual_hashrate': 0,
            'gpus': [
                {
                    'index': 0,
                    'hashrate': 60,
                    'dual_hashrate': 0,
                    'fan_speed': 20, # Miner reported fan speed
                    'accepted_shares': 10,
                    'rejected_shares': 1,
                    'temperature': 0,
                    'power_draw': 0
                }
            ]
        }
        mock_smi.return_value = [{'temperature': 60.0, 'power_draw': 150.0, 'fan_speed': 50.0}]

        data = miner_api.get_full_miner_data()
        self.assertIsNotNone(data)
        self.assertEqual(data['total_power_draw'], 150.0)
        self.assertEqual(data['avg_temperature'], 60.0)
        self.assertEqual(data['status'], 'Mining')
        self.assertEqual(data['gpus'][0]['temperature'], 60.0)
        self.assertEqual(data['gpus'][0]['fan_speed'], 50.0) # SMI should overwrite
        self.assertEqual(data['total_accepted_shares'], 10)
        self.assertEqual(data['avg_fan_speed'], 50.0)
        self.assertEqual(data['efficiency'], 120.0 / 150.0)
        self.assertEqual(data['gpus'][0]['efficiency'], 60.0 / 150.0)

    @patch('requests.get')
    def test_get_normalized_miner_data_multi_process(self, mock_get):
        # Mock responses for two miners on ports 4444 and 4445
        resp1 = MagicMock()
        resp1.json.return_value = {
            'Session': {'Uptime': 1000},
            'Total_Performance': [60.0, 0],
            'GPUs': [{'Performance': [60.0, 0], 'Fan_Speed': 50, 'Accepted_Shares': 5, 'Rejected_Shares': 0}]
        }
        resp2 = MagicMock()
        resp2.json.return_value = {
            'Session': {'Uptime': 1200},
            'Total_Performance': [70.0, 0],
            'GPUs': [{'Performance': [70.0, 0], 'Fan_Speed': 55, 'Accepted_Shares': 6, 'Rejected_Shares': 1}]
        }
        mock_get.side_effect = [resp1, resp2]

        # Use patch.dict to set environment variables
        with patch.dict(os.environ, {
            'MINER': 'lolminer',
            'MULTI_PROCESS': 'true',
            'GPU_DEVICES': '0,2',
            'API_PORT': '4444'
        }):
            data = miner_api.get_normalized_miner_data()
            self.assertIsNotNone(data)
            self.assertEqual(data['total_hashrate'], 130.0)
            self.assertEqual(data['uptime'], 1000) # min of 1000 and 1200
            self.assertEqual(len(data['gpus']), 2)
            self.assertEqual(data['gpus'][0]['index'], 0)
            self.assertEqual(data['gpus'][1]['index'], 2)
            self.assertEqual(data['gpus'][0]['hashrate'], 60.0)
            self.assertEqual(data['gpus'][1]['hashrate'], 70.0)

if __name__ == '__main__':
    unittest.main()
