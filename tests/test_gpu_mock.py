import unittest
import os
import sys

# Ensure current directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import miner_api

class TestGPUMock(unittest.TestCase):
    def setUp(self):
        # Save original env var
        self.original_mock = os.getenv('GPU_MOCK')

    def tearDown(self):
        # Restore original env var
        if self.original_mock is None:
            if 'GPU_MOCK' in os.environ:
                del os.environ['GPU_MOCK']
        else:
            os.environ['GPU_MOCK'] = self.original_mock

    def test_mock_mode_enabled(self):
        os.environ['GPU_MOCK'] = 'true'
        data = miner_api.get_full_miner_data()
        self.assertIsNotNone(data)
        self.assertEqual(data['miner'], 'lolminer (mock)')
        self.assertEqual(len(data['gpus']), 2)
        self.assertEqual(data['gpus'][0]['hashrate'], 120.5)
        self.assertEqual(data['status'], 'Mining')

        names = miner_api.get_gpu_names()
        self.assertEqual(names, ["Mock NVIDIA GeForce RTX 3080", "Mock NVIDIA GeForce RTX 3080"])

        smi = miner_api.get_gpu_smi_data()
        self.assertEqual(len(smi), 2)
        self.assertEqual(smi[0]['temperature'], 60.0)
        self.assertEqual(smi[0]['power_draw'], 200.0)
        self.assertEqual(smi[0]['fan_speed'], 50.0)

    def test_mock_mode_disabled(self):
        os.environ['GPU_MOCK'] = 'false'
        # We don't want to actually call SMI or Miner API in tests if they are not there,
        # but we want to make sure it doesn't return the mock data.
        data = miner_api.get_full_miner_data()
        if data:
            self.assertNotEqual(data.get('miner'), 'lolminer (mock)')

        names = miner_api.get_gpu_names()
        if names:
            self.assertNotEqual(names, ["Mock NVIDIA GeForce RTX 3080", "Mock NVIDIA GeForce RTX 3080"])

if __name__ == '__main__':
    unittest.main()
