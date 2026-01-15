import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import sys
import os
import subprocess

# Add the root directory to the Python path to allow importing 'metrics'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from metrics import update_metrics, HASHRATE, AVG_FAN_SPEED, TOTAL_POWER_DRAW, GPU_HASHRATE, GPU_TEMPERATURE, GPU_POWER_DRAW, GPU_FAN_SPEED, GPU_SHARES_ACCEPTED, GPU_SHARES_REJECTED

# Mock data for lolMiner API
mock_lolminer_api_data = {
    "Total_Performance": [120.5],
    "GPUs": [
        {"Performance": 60.2, "Fan_Speed": 55, "Accepted_Shares": 100, "Rejected_Shares": 2},
        {"Performance": 60.3, "Fan_Speed": 60, "Accepted_Shares": 110, "Rejected_Shares": 3}
    ]
}

# Mock data for nvidia-smi
mock_nvidia_smi_output = "35, 120.5\n40, 125.0\n"

# Mock data for rocm-smi
mock_rocm_smi_output = "card1,65,150.0W\ncard2,70,155.0W\n"

class TestMetrics(unittest.TestCase):
    @patch('subprocess.check_output')
    @patch('metrics.open', new_callable=mock_open)
    def test_update_metrics_nvidia(self, mock_open_file, mock_subprocess):
        # Configure the mock to simulate the NVIDIA environment
        mock_subprocess.side_effect = [
            json.dumps(mock_lolminer_api_data).encode(),  # lolMiner API
            b'/usr/bin/nvidia-smi',  # which nvidia-smi
            mock_nvidia_smi_output.encode()  # nvidia-smi command
        ]

        update_metrics()

        # Assertions for global metrics
        self.assertEqual(HASHRATE._value.get(), 120.5)
        self.assertAlmostEqual(AVG_FAN_SPEED._value.get(), 57.5)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 245.5)

        # Assertions for GPU 0
        self.assertEqual(GPU_HASHRATE.labels(gpu=0)._value.get(), 60.2)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=0)._value.get(), 35.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=0)._value.get(), 120.5)
        self.assertEqual(GPU_FAN_SPEED.labels(gpu=0)._value.get(), 55)
        self.assertEqual(GPU_SHARES_ACCEPTED.labels(gpu=0)._value.get(), 100)
        self.assertEqual(GPU_SHARES_REJECTED.labels(gpu=0)._value.get(), 2)

        # Assertions for GPU 1
        self.assertEqual(GPU_HASHRATE.labels(gpu=1)._value.get(), 60.3)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=1)._value.get(), 40.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=1)._value.get(), 125.0)
        self.assertEqual(GPU_FAN_SPEED.labels(gpu=1)._value.get(), 60)
        self.assertEqual(GPU_SHARES_ACCEPTED.labels(gpu=1)._value.get(), 110)
        self.assertEqual(GPU_SHARES_REJECTED.labels(gpu=1)._value.get(), 3)

    @patch('subprocess.check_output')
    @patch('metrics.open', new_callable=mock_open)
    def test_update_metrics_amd(self, mock_open_file, mock_subprocess):
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

        # Assertions for GPU 1
        self.assertEqual(GPU_TEMPERATURE.labels(gpu=1)._value.get(), 70.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu=1)._value.get(), 155.0)

    @patch('subprocess.check_output')
    @patch('metrics.open', new_callable=mock_open)
    def test_no_smi_tool(self, mock_open_file, mock_subprocess):
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

    @patch('subprocess.check_output')
    def test_api_error(self, mock_subprocess):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'curl')

        update_metrics()

        # Assert that metrics are reset to 0
        self.assertEqual(HASHRATE._value.get(), 0)
        self.assertEqual(AVG_FAN_SPEED._value.get(), 0)
        self.assertEqual(TOTAL_POWER_DRAW._value.get(), 0)

    @patch('subprocess.check_output')
    @patch('metrics.open', new_callable=mock_open)
    def test_no_gpus(self, mock_open_file, mock_subprocess):
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

if __name__ == '__main__':
    unittest.main()
