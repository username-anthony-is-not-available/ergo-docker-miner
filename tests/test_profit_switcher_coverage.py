import unittest
import time
import requests
import profit_switcher
from unittest.mock import MagicMock, patch

class TestProfitSwitcherCoverage(unittest.TestCase):

    def setUp(self):
        """Reset global variables in profit_switcher before each test."""
        profit_switcher._pool_score_cache = {}
        profit_switcher.last_switch_time = 0.0
        profit_switcher.start_time = time.time()

    def test_get_pool_profitability_cache_hit_details(self):
        pool = profit_switcher.POOLS[0]
        pool_url = pool["url"]
        details = {"score": 0.8, "effort": 1.2, "fee": 0.01}
        profit_switcher._pool_score_cache[pool_url] = {
            'timestamp': time.time(),
            'score': 0.8,
            'details': details
        }

        result = profit_switcher.get_pool_profitability(pool, return_details=True)
        self.assertEqual(result, details)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_invalid_json(self, mock_get):
        pool = profit_switcher.POOLS[0]
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        result = profit_switcher.get_pool_profitability(pool, return_details=True)
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["effort"], 1.0)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_2miners_list_luck(self, mock_get):
        pool = {"name": "2Miners", "url": "url", "type": "2miners", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": [150]}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 0.66)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_2miners_string_luck(self, mock_get):
        pool = {"name": "2Miners", "url": "url", "type": "2miners", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": "200"}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 0.495)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_nanopool_direct_luck(self, mock_get):
        pool = {"name": "Nanopool", "url": "url", "type": "nanopool", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": 50}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 1.98)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_nanopool_alt_format(self, mock_get):
        pool = {"name": "Nanopool", "url": "url", "type": "nanopool", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"luck": 50}}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 1.98)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_woolypooly_luck(self, mock_get):
        pool = {"name": "WoolyPooly", "url": "url", "type": "woolypooly", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": 120}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 0.825)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_woolypooly_effort(self, mock_get):
        pool = {"name": "WoolyPooly", "url": "url", "type": "woolypooly", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"effort": 120}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 0.825)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_parsing_error(self, mock_get):
        pool = {"name": "2Miners", "url": "url", "type": "2miners", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": None}
        mock_get.return_value = mock_response

        score = profit_switcher.get_pool_profitability(pool)
        self.assertAlmostEqual(score, 0.99)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_return_details_success(self, mock_get):
        pool = {"name": "Test", "url": "url", "type": "other", "fee": 0.01}
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        result = profit_switcher.get_pool_profitability(pool, return_details=True)
        self.assertEqual(result, {"score": 0.99, "effort": 1.0, "fee": 0.01})

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_network_error(self, mock_get):
        pool = {"name": "Test", "url": "url", "type": "other", "fee": 0.01}
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        score = profit_switcher.get_pool_profitability(pool)
        self.assertEqual(score, 0.0)

    @patch('profit_switcher.requests.get')
    def test_get_pool_profitability_unexpected_error(self, mock_get):
        pool = {"name": "Test", "url": "url", "type": "other", "fee": 0.01}
        mock_get.side_effect = Exception("Unexpected")

        score = profit_switcher.get_pool_profitability(pool)
        self.assertEqual(score, 0.0)

    @patch('profit_switcher.read_env_file')
    @patch('time.sleep')
    def test_main_auto_switching_disabled(self, mock_sleep, mock_read_env):
        mock_read_env.side_effect = [
            {"AUTO_PROFIT_SWITCHING": "false"},
            Exception("Stop loop")
        ]
        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Stop loop":
                raise e
        mock_sleep.assert_any_call(60)

    @patch('profit_switcher.read_env_file')
    @patch('time.sleep')
    def test_main_initial_grace_period(self, mock_sleep, mock_read_env):
        mock_read_env.side_effect = [
            {"AUTO_PROFIT_SWITCHING": "true", "MIN_SWITCH_COOLDOWN": "900"},
            Exception("Stop loop")
        ]
        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Stop loop":
                raise e
        mock_sleep.assert_any_call(60)

    @patch('profit_switcher.read_env_file')
    @patch('time.sleep')
    def test_main_cooldown_active(self, mock_sleep, mock_read_env):
        mock_read_env.side_effect = [
            {"AUTO_PROFIT_SWITCHING": "true", "MIN_SWITCH_COOLDOWN": "900"},
            Exception("Stop loop")
        ]
        profit_switcher.start_time = time.time() - 1000
        profit_switcher.last_switch_time = time.time() - 500
        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Stop loop":
                raise e
        mock_sleep.assert_any_call(60)

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('time.sleep')
    def test_main_custom_pool_match(self, mock_sleep, mock_get_profit, mock_read_env):
        mock_read_env.side_effect = [
            {
                "AUTO_PROFIT_SWITCHING": "true",
                "POOL_ADDRESS": "custom-stratum",
                "PROFIT_SWITCHING_THRESHOLD": "0.1",
                "MIN_SWITCH_COOLDOWN": "0"
            },
            Exception("Stop loop")
        ]
        profit_switcher.start_time = time.time() - 2000

        test_pools = [
            {"name": "Other", "stratum": "other-stratum", "url": "url1", "fee": 0.01},
            {"name": "MatchMe", "stratum": "custom-stratum", "url": "url2", "fee": 0.01}
        ]
        with patch('profit_switcher.POOLS', test_pools):
            mock_get_profit.side_effect = [1.0, 0.0, 0.5]
            try:
                profit_switcher.main()
            except Exception as e:
                if str(e) != "Stop loop":
                    raise e

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('time.sleep')
    def test_main_custom_pool_default_score(self, mock_sleep, mock_get_profit, mock_read_env):
        mock_read_env.side_effect = [
            {
                "AUTO_PROFIT_SWITCHING": "true",
                "POOL_ADDRESS": "truly-custom-stratum",
                "PROFIT_SWITCHING_THRESHOLD": "0.1",
                "MIN_SWITCH_COOLDOWN": "0"
            },
            Exception("Stop loop")
        ]
        profit_switcher.start_time = time.time() - 2000
        mock_get_profit.return_value = 0.5
        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Stop loop":
                raise e

    @patch('profit_switcher.read_env_file')
    @patch('profit_switcher.get_pool_profitability')
    @patch('time.sleep')
    def test_main_already_on_best_pool(self, mock_sleep, mock_get_profit, mock_read_env):
        mock_read_env.side_effect = [
            {
                "AUTO_PROFIT_SWITCHING": "true",
                "POOL_ADDRESS": profit_switcher.POOLS[0]["stratum"],
                "MIN_SWITCH_COOLDOWN": "0"
            },
            Exception("Stop loop")
        ]
        profit_switcher.start_time = time.time() - 2000
        def mock_get_profit_side_effect(pool):
            if pool["name"] == profit_switcher.POOLS[0]["name"]:
                return 2.0
            return 1.0
        mock_get_profit.side_effect = mock_get_profit_side_effect
        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Stop loop":
                raise e

    @patch('profit_switcher.read_env_file')
    @patch('time.sleep')
    def test_main_exception_in_loop(self, mock_sleep, mock_read_env):
        mock_read_env.side_effect = [
            Exception("Error"),
            Exception("Stop loop")
        ]
        try:
            profit_switcher.main()
        except Exception as e:
            if str(e) != "Stop loop":
                raise e
        self.assertTrue(mock_sleep.called)

if __name__ == '__main__':
    unittest.main()
