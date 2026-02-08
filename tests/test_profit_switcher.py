import unittest
from unittest.mock import patch, MagicMock
import profit_switcher
import os

class TestProfitSwitcher(unittest.TestCase):

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_2miners(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": 120}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        pool = profit_switcher.POOLS[0] # 2Miners
        score = profit_switcher.get_pool_profitability(pool)
        # Score = (1 - 0.01) / 1.0 = 0.99 (Since 2miners effort is currently hardcoded to 1.0 in the impl)
        self.assertAlmostEqual(score, 0.99)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_herominers(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"effort_1d": 0.8}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        pool = profit_switcher.POOLS[1] # HeroMiners
        score = profit_switcher.get_pool_profitability(pool)
        # Score = (1 - 0.009) / 0.8 = 0.991 / 0.8 = 1.23875
        self.assertAlmostEqual(score, 1.23875)

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.write_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('profit_switcher.subprocess.run')
    @patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    def test_main_loop_switching(self, mock_sleep, mock_run, mock_get_profit, mock_write_env, mock_read_env):
        # Current pool is 2Miners
        mock_read_env.return_value = {
            "AUTO_PROFIT_SWITCHING": "true",
            "POOL_ADDRESS": "stratum+tcp://erg.2miners.com:8080",
            "PROFIT_SWITCHING_THRESHOLD": "0.1", # 10%
            "PROFIT_SWITCHING_INTERVAL": "1800"
        }

        # Use a dictionary to return consistent scores based on pool name
        scores = {
            "2Miners": 0.99,
            "HeroMiners": 1.2,
            "Nanopool": 1.0,
            "WoolyPooly": 1.05
        }
        mock_get_profit.side_effect = lambda pool: scores[pool["name"]]

        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Break Loop":
                raise e

        # Verify write_env_file was called with HeroMiners address
        mock_write_env.assert_called_once()
        args, _ = mock_write_env.call_args
        self.assertEqual(args[0]["POOL_ADDRESS"], "stratum+tcp://herominers.com:1180")

        # Verify restart.sh was called
        mock_run.assert_called_once_with(["./restart.sh"], check=True)

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('profit_switcher.write_env_file')
    @patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    def test_main_loop_no_switching_below_threshold(self, mock_sleep, mock_write, mock_get_profit, mock_read_env):
        # Current pool is 2Miners
        mock_read_env.return_value = {
            "AUTO_PROFIT_SWITCHING": "true",
            "POOL_ADDRESS": "stratum+tcp://erg.2miners.com:8080"
        }

        # HeroMiners is only slightly more profitable (below 0.5% threshold)
        mock_get_profit.side_effect = [0.99, 0.991, 0.99, 0.991]

        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Break Loop":
                raise e

        # Verify write_env_file was NOT called
        mock_write.assert_not_called()

if __name__ == '__main__':
    unittest.main()
