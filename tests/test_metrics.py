import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import sys
import os
import subprocess
import time

# Add the root directory to the Python path to allow importing 'metrics'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import metrics
from metrics import update_metrics, HASHRATE, DUAL_HASHRATE, AVG_FAN_SPEED, TOTAL_POWER_DRAW, GPU_HASHRATE, GPU_DUAL_HASHRATE, GPU_TEMPERATURE, GPU_POWER_DRAW, GPU_FAN_SPEED, GPU_SHARES_ACCEPTED, GPU_SHARES_REJECTED

# Mock data for Normalized Miner API (lolMiner)
mock_normalized_lolminer_data = {
    "miner": "lolminer",
    "uptime": 1000,
    "total_hashrate": 120.5,
    "total_dual_hashrate": 0,
    "gpus": [
        {"index": 0, "hashrate": 60.2, "dual_hashrate": 0, "fan_speed": 55, "accepted_shares": 100, "rejected_shares": 2, "temperature": 0, "power_draw": 0},
        {"index": 1, "hashrate": 60.3, "dual_hashrate": 0, "fan_speed": 60, "accepted_shares": 110, "rejected_shares": 3, "temperature": 0, "power_draw": 0}
    ]
}

# Mock data for Normalized Miner API (lolMiner Dual)
mock_normalized_lolminer_dual_data = {
    "miner": "lolminer",
    "uptime": 1000,
    "total_hashrate": 120.5,
    "total_dual_hashrate": 250.5,
    "gpus": [
        {"index": 0, "hashrate": 60.2, "dual_hashrate": 125.2, "fan_speed": 55, "accepted_shares": 100, "rejected_shares": 2, "temperature": 0, "power_draw": 0},
        {"index": 1, "hashrate": 60.3, "dual_hashrate": 125.3, "fan_speed": 60, "accepted_shares": 110, "rejected_shares": 3, "temperature": 0, "power_draw": 0}
    ]
}

# Mock data for Normalized Miner API (T-Rex)
mock_normalized_trex_data = {
    "miner": "t-rex",
    "uptime": 2000,
    "total_hashrate": 125.0,
    "total_dual_hashrate": 0,
    "gpus": [
        {"index": 0, "hashrate": 62.0, "dual_hashrate": 0, "fan_speed": 65, "accepted_shares": 200, "rejected_shares": 5, "temperature": 35.0, "power_draw": 120.5},
        {"index": 1, "hashrate": 63.0, "dual_hashrate": 0, "fan_speed": 70, "accepted_shares": 220, "rejected_shares": 6, "temperature": 40.0, "power_draw": 125.0}
    ]
}

# Mock data for SMI
mock_gpu_stats_nvidia = [
    {'temperature': 35.0, 'power_draw': 120.5},
    {'temperature': 40.0, 'power_draw': 125.0}
]

mock_gpu_stats_amd = [
    {'temperature': 65.0, 'power_draw': 150.0},
    {'temperature': 70.0, 'power_draw': 155.0}
]

class TestMetrics(unittest.TestCase):
    def setUp(self):
        metrics.last_prune_time = 0
        # Reset Prometheus metrics
        HASHRATE.set(0)
        DUAL_HASHRATE.set(0)
        AVG_FAN_SPEED.set(0)
        TOTAL_POWER_DRAW.set(0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    def test_update_metrics_nvidia_lolminer(self, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        mock_miner_data.return_value = mock_normalized_lolminer_data
        mock_smi_data.return_value = mock_gpu_stats_nvidia

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertEqual(DUAL_HASHRATE._value.get(), 0)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 57.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 245.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu="0")._value.get(), 60.2)
        self.assertEqual(GPU_DUAL_HASHRATE.labels(gpu="0")._value.get(), 0)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu="0")._value.get(), 35.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu="0")._value.get(), 120.5)
        self.assertEqual(GPU_FAN_SPEED.labels(gpu="0")._value.get(), 55)
        self.assertEqual(GPU_SHARES_ACCEPTED.labels(gpu="0")._value.get(), 100)
        self.assertEqual(GPU_SHARES_REJECTED.labels(gpu="0")._value.get(), 2)

        # Assert log_history call
        # hashrate, avg_temp, avg_fan, accepted, rejected, dual
        # avg_temp = (35+40)/2 = 37.5
        # accepted = 100+110 = 210
        # rejected = 2+3 = 5
        mock_log.assert_called_once_with(120.5, 37.5, 57.5, 210, 5, 0)
        mock_prune.assert_called_once()

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    def test_update_metrics_lolminer_dual(self, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        mock_miner_data.return_value = mock_normalized_lolminer_dual_data
        mock_smi_data.return_value = mock_gpu_stats_nvidia

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertEqual(DUAL_HASHRATE._value.get(), 250.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu="0")._value.get(), 60.2)
        self.assertEqual(GPU_DUAL_HASHRATE.labels(gpu="0")._value.get(), 125.2)

        # Assert log_history call
        mock_log.assert_called_once_with(120.5, 37.5, 57.5, 210, 5, 250.5)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    def test_update_metrics_nvidia_trex(self, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        mock_miner_data.return_value = mock_normalized_trex_data
        mock_smi_data.return_value = mock_gpu_stats_nvidia

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 125)
        self.assertEqual(DUAL_HASHRATE._value.get(), 0)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 67.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 245.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu="0")._value.get(), 62)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu="0")._value.get(), 35.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu="0")._value.get(), 120.5)
        self.assertEqual(GPU_FAN_SPEED.labels(gpu="0")._value.get(), 65)
        self.assertEqual(GPU_SHARES_ACCEPTED.labels(gpu="0")._value.get(), 200)
        self.assertEqual(GPU_SHARES_REJECTED.labels(gpu="0")._value.get(), 5)

        # Assert log_history call
        mock_log.assert_called_once_with(125, 37.5, 67.5, 420, 11, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    def test_update_metrics_amd(self, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        mock_miner_data.return_value = mock_normalized_lolminer_data
        mock_smi_data.return_value = mock_gpu_stats_amd

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 57.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 305.0)

        # Assertions for GPU 0
        self.assertEqual(GPU_TEMPERATURE.labels(gpu="0")._value.get(), 65.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu="0")._value.get(), 150.0)

        # Assert log_history call
        mock_log.assert_called_once_with(120.5, 67.5, 57.5, 210, 5, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    def test_no_smi_tool(self, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        mock_miner_data.return_value = mock_normalized_lolminer_data
        mock_smi_data.return_value = [] # No SMI tool found

        update_metrics()

        # Assert that power and temperature are 0 (from SMI, but miner might have some if T-Rex)
        # For lolminer they will be 0
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 0)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu="0")._value.get(), 0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu="0")._value.get(), 0)
        mock_log.assert_called_once_with(120.5, 0.0, 57.5, 210, 5, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_normalized_miner_data')
    def test_api_error(self, mock_miner_data, mock_prune, mock_log):
        mock_miner_data.return_value = None

        update_metrics()

        # Assert that metrics are reset to 0
        self.assertEqual(HASHRATE._value.get(), 0)
        self.assertEqual(DUAL_HASHRATE._value.get(), 0)
        self.assertEqual(AVG_FAN_SPEED._value.get(), 0)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 0)
        # log_history should NOT be called on error
        mock_log.assert_not_called()

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    def test_no_gpus(self, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        # Mock API data with no GPUs
        mock_miner_data.return_value = {"miner": "lolminer", "total_hashrate": 0, "gpus": []}
        mock_smi_data.return_value = []

        update_metrics()

        self.assertEqual(HASHRATE._value.get(), 0)
        self.assertEqual(AVG_FAN_SPEED._value.get(), 0)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 0)
        mock_log.assert_called_once_with(0, 0, 0, 0, 0, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_gpu_smi_data')
    @patch('metrics.get_normalized_miner_data')
    @patch('time.time')
    def test_prune_frequency(self, mock_time, mock_miner_data, mock_smi_data, mock_prune, mock_log):
        mock_miner_data.return_value = mock_normalized_lolminer_data
        mock_smi_data.return_value = []

        # First call, time is 10000. last_prune_time is 0. 10000 > 3600, so prune.
        mock_time.return_value = 10000
        update_metrics()
        self.assertEqual(mock_prune.call_count, 1)

        # Second call, time is 11000. 11000 - 10000 = 1000 < 3600, so NO prune.
        mock_time.return_value = 11000
        update_metrics()
        self.assertEqual(mock_prune.call_count, 1)

        # Third call, time is 14000. 14000 - 10000 = 4000 > 3600, so prune.
        mock_time.return_value = 14000
        update_metrics()
        self.assertEqual(mock_prune.call_count, 2)

if __name__ == '__main__':
    unittest.main()
