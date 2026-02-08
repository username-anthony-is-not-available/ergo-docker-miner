import unittest
from unittest.mock import patch
import miner_api

class TestMinerApiEnhancements(unittest.TestCase):
    @patch('database.get_history')
    def test_get_24h_average_hashrate(self, mock_get_history):
        # Mock history data
        mock_get_history.return_value = [
            {'hashrate': 100.0},
            {'hashrate': 110.0},
            {'hashrate': 120.0}
        ]

        avg = miner_api.get_24h_average_hashrate()
        self.assertEqual(avg, 110.0)
        mock_get_history.assert_called_once_with(days=1)

    @patch('database.get_history')
    def test_get_24h_average_hashrate_empty(self, mock_get_history):
        mock_get_history.return_value = []
        avg = miner_api.get_24h_average_hashrate()
        self.assertEqual(avg, 0.0)

if __name__ == '__main__':
    unittest.main()
