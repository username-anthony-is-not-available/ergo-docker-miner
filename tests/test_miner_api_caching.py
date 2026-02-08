import unittest
from unittest.mock import patch, MagicMock
import miner_api
import os

class TestMinerApiCaching(unittest.TestCase):
    def setUp(self):
        # Reset cache before each test
        miner_api._gpu_names_cache = []

    @patch('miner_api.subprocess.check_output')
    def test_get_gpu_names_caching(self, mock_output):
        mock_output.side_effect = [
            b'/usr/bin/nvidia-smi',
            b'GPU 0: RTX 3070\nGPU 1: RTX 3080\n'
        ]

        # First call
        names1 = miner_api.get_gpu_names()
        self.assertEqual(len(names1), 2)
        self.assertEqual(names1[0], "GPU 0: RTX 3070")

        # Second call should use cache (mock_output should not be called again for smi)
        names2 = miner_api.get_gpu_names()
        self.assertEqual(names1, names2)
        # 1 for 'which nvidia-smi', 1 for 'nvidia-smi ...'
        self.assertEqual(mock_output.call_count, 2)

    @patch('miner_api.subprocess.check_output')
    @patch('miner_api._fetch_single_miner_data')
    @patch('os.getenv')
    def test_get_normalized_miner_data_multi_process_auto(self, mock_getenv, mock_fetch, mock_output):
        def getenv_side_effect(key, default=None):
            vals = {
                'MINER': 'lolminer',
                'API_PORT': '4444',
                'MULTI_PROCESS': 'true',
                'GPU_DEVICES': 'AUTO'
            }
            return vals.get(key, default)
        mock_getenv.side_effect = getenv_side_effect

        # Mock nvidia-smi returning 2 GPUs
        mock_output.return_value = b'0\n1\n'

        # Mock fetch_single_miner_data
        mock_fetch.side_effect = [
            {'miner': 'lolminer', 'uptime': 100, 'total_hashrate': 50, 'total_dual_hashrate': 0, 'gpus': [{'index': 0, 'hashrate': 50}]},
            {'miner': 'lolminer', 'uptime': 120, 'total_hashrate': 60, 'total_dual_hashrate': 0, 'gpus': [{'index': 0, 'hashrate': 60}]}
        ]

        data = miner_api.get_normalized_miner_data()
        self.assertIsNotNone(data)
        self.assertEqual(data['total_hashrate'], 110)
        self.assertEqual(len(data['gpus']), 2)
        self.assertEqual(data['gpus'][0]['index'], 0)
        self.assertEqual(data['gpus'][1]['index'], 1)

if __name__ == '__main__':
    unittest.main()
