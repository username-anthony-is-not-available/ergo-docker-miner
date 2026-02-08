import unittest
from unittest.mock import patch, MagicMock
import time
import profit_switcher

class TestProfitSwitcherCaching(unittest.TestCase):
    def setUp(self):
        # Clear cache before each test
        profit_switcher._pool_score_cache = {}

    @patch('requests.get')
    def test_caching_logic(self, mock_get):
        pool = {
            "name": "TestPool",
            "url": "http://test.com/api",
            "stratum": "stratum+tcp://test.com:1234",
            "type": "2miners",
            "fee": 0.01
        }

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": 100.0}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # First call should hit the API
        score1 = profit_switcher.get_pool_profitability(pool, use_cache=True)
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(score1, 0.99)

        # Second call should use cache
        score2 = profit_switcher.get_pool_profitability(pool, use_cache=True)
        self.assertEqual(mock_get.call_count, 1) # Still 1
        self.assertEqual(score2, 0.99)

        # Third call with use_cache=False should hit the API again
        score3 = profit_switcher.get_pool_profitability(pool, use_cache=False)
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(score3, 0.99)

    @patch('requests.get')
    def test_cache_expiration(self, mock_get):
        pool = {
            "name": "TestPool",
            "url": "http://test.com/api",
            "stratum": "stratum+tcp://test.com:1234",
            "type": "2miners",
            "fee": 0.01
        }

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"luck": 100.0}
        mock_get.return_value = mock_response

        # Set CACHE_TTL to 0 for testing expiration
        original_ttl = profit_switcher.CACHE_TTL
        profit_switcher.CACHE_TTL = 0
        try:
            profit_switcher.get_pool_profitability(pool, use_cache=True)
            self.assertEqual(mock_get.call_count, 1)

            # Should hit API again because TTL is 0
            profit_switcher.get_pool_profitability(pool, use_cache=True)
            self.assertEqual(mock_get.call_count, 2)
        finally:
            profit_switcher.CACHE_TTL = original_ttl

if __name__ == '__main__':
    unittest.main()
