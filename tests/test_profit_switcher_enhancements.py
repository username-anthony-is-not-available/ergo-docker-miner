import unittest
from unittest.mock import patch, MagicMock
import profit_switcher
import time

class TestProfitSwitcherEnhancements(unittest.TestCase):
    def setUp(self):
        # Reset global state to avoid cross-test interference
        profit_switcher.last_switch_time = 0.0
        profit_switcher.start_time = time.time()

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    def test_configurable_cooldown(self, mock_sleep, mock_get_profit, mock_read_env):
        # Move start_time back so it's between 500 and 1000
        profit_switcher.start_time = time.time() - 600

        # Set cooldown to 1000
        mock_read_env.return_value = {
            "AUTO_PROFIT_SWITCHING": "true",
            "MIN_SWITCH_COOLDOWN": "1000"
        }

        with patch('profit_switcher.logger.info') as mock_info:
            try:
                profit_switcher.main()
            except Exception as e:
                if str(e) != "Break Loop": raise e

            # Should have skipped due to grace period
            any_grace = any("initial grace period" in call.args[0] for call in mock_info.call_args_list)
            self.assertTrue(any_grace)

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    def test_score_caching(self, mock_sleep, mock_get_profit, mock_read_env):
        profit_switcher.start_time = time.time() - 2000

        mock_read_env.return_value = {
            "AUTO_PROFIT_SWITCHING": "true",
            "POOL_ADDRESS": "stratum+tcp://erg.2miners.com:8080",
            "PROFIT_SWITCHING_THRESHOLD": "0.01"
        }

        # 4 pools in POOLS list. get_pool_profitability should be called exactly 4 times if caching works.
        mock_get_profit.side_effect = [1.0, 1.1, 1.0, 1.0] # 2Miners, HeroMiners, Nanopool, WoolyPooly

        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Break Loop": raise e

        self.assertEqual(mock_get_profit.call_count, 4)

if __name__ == '__main__':
    unittest.main()
