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

# Mock data for lolMiner API
mock_lolminer_api_data = {
    "Total_Performance": [120.5],
    "GPUs": [
        {"Performance": [60.2], "Fan_Speed": 55, "Accepted_Shares": 100, "Rejected_Shares": 2},
        {"Performance": [60.3], "Fan_Speed": 60, "Accepted_Shares": 110, "Rejected_Shares": 3}
    ]
}

# Mock data for lolMiner API with Dual Mining
mock_lolminer_dual_api_data = {
    "Total_Performance": [120.5, 250.5],
    "GPUs": [
        {"Performance": [60.2, 125.2], "Fan_Speed": 55, "Accepted_Shares": 100, "Rejected_Shares": 2},
        {"Performance": [60.3, 125.3], "Fan_Speed": 60, "Accepted_Shares": 110, "Rejected_Shares": 3}
    ]
}

# Mock data for T-Rex API
mock_trex_api_data = {
    "hashrate": 125000000,
    "gpus": [
        {
            "hashrate": 62000000,
            "fan_speed": 65,
            "shares": {"accepted_count": 200, "rejected_count": 5}
        },
        {
            "hashrate": 63000000,
            "fan_speed": 70,
            "shares": {"accepted_count": 220, "rejected_count": 6}
        }
    ]
}


# Mock data for nvidia-smi
mock_nvidia_smi_output = "35, 120.5\n40, 125.0\n"

# Mock data for rocm-smi
mock_rocm_smi_output = "card1,65,150.0W\ncard2,70,155.0W\n"

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
    @patch('subprocess.check_output')
    @patch.dict(os.environ, {"MINER": "lolminer"})
    def test_update_metrics_nvidia_lolminer(self, mock_subprocess, mock_prune, mock_log):
        # Configure the mock to simulate the NVIDIA environment
        mock_subprocess.side_effect = [
            json.dumps(mock_lolminer_api_data).encode(),  # lolMiner API
            b'/usr/bin/nvidia-smi',  # which nvidia-smi
            mock_nvidia_smi_output.encode()  # nvidia-smi command
        ]

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertEqual(DUAL_HASHRATE._value.get(), 0)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 57.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 245.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu=0)._value.get(), 60.2)
        self.assertEqual(GPU_DUAL_HASHRATE.labels(gpu=0)._value.get(), 0)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=0)._value.get(), 35.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=0)._value.get(), 120.5)
        self.assertEqual(GPU_FAN_SPEED.labels(gpu=0)._value.get(), 55)
        self.assertEqual(GPU_SHARES_ACCEPTED.labels(gpu=0)._value.get(), 100)
        self.assertEqual(GPU_SHARES_REJECTED.labels(gpu=0)._value.get(), 2)

        # Assert log_history call
        mock_log.assert_called_once_with(120.5, 37.5, 57.5, 210, 5, 0)
        mock_prune.assert_called_once()

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('subprocess.check_output')
    @patch.dict(os.environ, {"MINER": "lolminer"})
    def test_update_metrics_lolminer_dual(self, mock_subprocess, mock_prune, mock_log):
        # Configure the mock to simulate the lolMiner Dual Mining
        mock_subprocess.side_effect = [
            json.dumps(mock_lolminer_dual_api_data).encode(),  # lolMiner API
            b'/usr/bin/nvidia-smi',  # which nvidia-smi
            mock_nvidia_smi_output.encode()  # nvidia-smi command
        ]

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertEqual(DUAL_HASHRATE._value.get(), 250.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu=0)._value.get(), 60.2)
        self.assertEqual(GPU_DUAL_HASHRATE.labels(gpu=0)._value.get(), 125.2)

        # Assert log_history call
        mock_log.assert_called_once_with(120.5, 37.5, 57.5, 210, 5, 250.5)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('subprocess.check_output')
    @patch.dict(os.environ, {"MINER": "t-rex"})
    def test_update_metrics_nvidia_trex(self, mock_subprocess, mock_prune, mock_log):
        # Configure the mock to simulate the NVIDIA environment
        mock_subprocess.side_effect = [
            json.dumps(mock_trex_api_data).encode(),  # T-Rex API
            b'/usr/bin/nvidia-smi',  # which nvidia-smi
            mock_nvidia_smi_output.encode()  # nvidia-smi command
        ]

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 125)
        self.assertEqual(DUAL_HASHRATE._value.get(), 0)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 67.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 245.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu=0)._value.get(), 62)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=0)._value.get(), 35.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=0)._value.get(), 120.5)
        self.assertEqual(GPU_FAN_SPEED.labels(gpu=0)._value.get(), 65)
        self.assertEqual(GPU_SHARES_ACCEPTED.labels(gpu=0)._value.get(), 200)
        self.assertEqual(GPU_SHARES_REJECTED.labels(gpu=0)._value.get(), 5)

        # Assert log_history call
        mock_log.assert_called_once_with(125, 37.5, 67.5, 420, 11, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('subprocess.check_output')
    def test_update_metrics_amd(self, mock_subprocess, mock_prune, mock_log):
        # Configure the mock to simulate the AMD environment
        mock_subprocess.side_effect = [
            json.dumps(mock_lolminer_api_data).encode(),  # lolMiner API
            subprocess.CalledProcessError(1, 'which'), # nvidia-smi fails
            b'/usr/bin/rocm-smi',  # which rocm-smi
            mock_rocm_smi_output.encode()  # rocm-smi command
        ]

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 57.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 305.0)

        # Assertions for GPU 0
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=0)._value.get(), 65.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=0)._value.get(), 150.0)

        # Assert log_history call
        mock_log.assert_called_once_with(120.5, 67.5, 57.5, 210, 5, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('subprocess.check_output')
    def test_no_smi_tool(self, mock_subprocess, mock_prune, mock_log):
        mock_subprocess.side_effect = [
            json.dumps(mock_lolminer_api_data).encode(), # lolMiner API call
            subprocess.CalledProcessError(1, 'which'), # nvidia-smi fails
            subprocess.CalledProcessError(1, 'which') # rocm-smi fails
        ]

        update_metrics()

        # Assert that power and temperature are 0
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 0)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=0)._value.get(), 0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=0)._value.get(), 0)
        mock_log.assert_called_once_with(120.5, 0.0, 57.5, 210, 5, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('subprocess.check_output')
    def test_api_error(self, mock_subprocess, mock_prune, mock_log):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'curl')

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
    @patch('subprocess.check_output')
    def test_no_gpus(self, mock_subprocess, mock_prune, mock_log):
        # Mock API data with no GPUs
        mock_api_no_gpus = {"Total_Performance": [0], "GPUs": []}
        mock_subprocess.side_effect = [
            json.dumps(mock_api_no_gpus).encode(), # lolMiner API call
            subprocess.CalledProcessError(1, 'which'), # nvidia-smi fails
            subprocess.CalledProcessError(1, 'which') # rocm-smi fails
        ]

        update_metrics()

        self.assertEqual(HASHRATE._value.get(), 0)
        self.assertEqual(AVG_FAN_SPEED._value.get(), 0)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 0)
        mock_log.assert_called_once_with(0, 0, 0, 0, 0, 0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('subprocess.check_output')
    @patch('time.time')
    def test_prune_frequency(self, mock_time, mock_subprocess, mock_prune, mock_log):
        # Mock API data and SMI detection failures to keep it simple
        mock_subprocess.side_effect = [
            json.dumps(mock_lolminer_api_data).encode(), # call 1: API
            subprocess.CalledProcessError(1, 'which'), # call 1: nvidia-smi
            subprocess.CalledProcessError(1, 'which'), # call 1: rocm-smi
            json.dumps(mock_lolminer_api_data).encode(), # call 2: API
            subprocess.CalledProcessError(1, 'which'), # call 2: nvidia-smi
            subprocess.CalledProcessError(1, 'which'), # call 2: rocm-smi
            json.dumps(mock_lolminer_api_data).encode(), # call 3: API
            subprocess.CalledProcessError(1, 'which'), # call 3: nvidia-smi
            subprocess.CalledProcessError(1, 'which'), # call 3: rocm-smi
        ]

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
