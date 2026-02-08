import unittest
import sys
import os

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from miner_api import parse_lolminer_data

class TestParsing(unittest.TestCase):
    def test_parse_lolminer_standard(self):
        raw_data = {
            "Session": {
                "Uptime": 3600,
                "Algorithm": "Autolykos2",
                "Driver": "535.129.03"
            },
            "Total_Performance": [120.5, 250.0],
            "GPUs": [
                {
                    "Index": 0,
                    "Name": "NVIDIA GeForce RTX 3080",
                    "Performance": [60.2, 125.0],
                    "Fan_Speed": 50,
                    "Accepted_Shares": 10,
                    "Rejected_Shares": 1
                }
            ]
        }
        normalized = parse_lolminer_data(raw_data)
        self.assertEqual(normalized['miner'], 'lolminer')
        self.assertEqual(normalized['uptime'], 3600)
        self.assertEqual(normalized['total_hashrate'], 120.5)
        self.assertEqual(normalized['total_dual_hashrate'], 250.0)
        self.assertEqual(normalized['driver_version'], '535')
        self.assertEqual(len(normalized['gpus']), 1)
        self.assertEqual(normalized['gpus'][0]['hashrate'], 60.2)
        self.assertEqual(normalized['gpus'][0]['dual_hashrate'], 125.0)

    def test_parse_lolminer_no_driver(self):
        raw_data = {
            "Session": {"Uptime": 100},
            "Total_Performance": [50.0],
            "GPUs": []
        }
        normalized = parse_lolminer_data(raw_data)
        self.assertEqual(normalized['driver_version'], 'unknown')

    def test_parse_lolminer_unusual_driver_format(self):
        raw_data = {
            "Session": {"Driver": "Version 525.60.11"},
            "Total_Performance": [10.0],
            "GPUs": []
        }
        # My regex was ^(\d+). So "Version 525" won't match if it's at the start.
        # Wait, let's re-check the regex: re.search(r'^(\d+)', driver_str)
        # If it's "Version 525", it won't match.
        normalized = parse_lolminer_data(raw_data)
        self.assertEqual(normalized['driver_version'], 'unknown')

        # Test format that should match
        raw_data["Session"]["Driver"] = "470.103.01"
        normalized = parse_lolminer_data(raw_data)
        self.assertEqual(normalized['driver_version'], '470')

    def test_parse_lolminer_missing_total_perf(self):
        raw_data = {
            "Session": {"Uptime": 100},
            "GPUs": []
        }
        normalized = parse_lolminer_data(raw_data)
        self.assertEqual(normalized['total_hashrate'], 0)
        self.assertEqual(normalized['total_dual_hashrate'], 0)

    def test_parse_lolminer_gpu_single_perf_value(self):
        # Some lolminer versions might return a single number for Performance instead of a list
        raw_data = {
            "GPUs": [
                {
                    "Performance": 60.2,
                    "Fan_Speed": 50
                }
            ]
        }
        normalized = parse_lolminer_data(raw_data)
        self.assertEqual(normalized['gpus'][0]['hashrate'], 60.2)
        self.assertEqual(normalized['gpus'][0]['dual_hashrate'], 0)

if __name__ == '__main__':
    unittest.main()
