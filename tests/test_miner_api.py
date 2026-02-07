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
                return b'60, 120\n65, 130'
            raise subprocess.CalledProcessError(1, cmd)

        mock_check_output.side_effect = side_effect

        data = miner_api.get_gpu_smi_data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['temperature'], 60.0)
        self.assertEqual(data[0]['power_draw'], 120.0)

    @patch('subprocess.check_output')
    def test_get_gpu_smi_data_amd(self, mock_check_output):
        def side_effect(cmd, *args, **kwargs):
            if cmd == ['which', 'nvidia-smi']:
                raise subprocess.CalledProcessError(1, cmd)
            if cmd == ['which', 'rocm-smi']:
                return b'/usr/bin/rocm-smi'
            if 'rocm-smi --showtemp' in cmd:
                # card,temp,power
                return b'0,55.0,100.0W\n1,58.0,110.0W'
            raise subprocess.CalledProcessError(1, cmd)

        mock_check_output.side_effect = side_effect

        data = miner_api.get_gpu_smi_data()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['temperature'], 55.0)
        self.assertEqual(data[0]['power_draw'], 100.0)

if __name__ == '__main__':
    unittest.main()
