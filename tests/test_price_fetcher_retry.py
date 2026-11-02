import unittest
from unittest.mock import MagicMock, patch

import requests

import price_fetcher


class PriceFetcherRetryTests(unittest.TestCase):
    def test_fetch_price_retries_transient_connection_failure(self) -> None:
        response = MagicMock()
        response.json.return_value = {"ergo": {"usd": 1.25}}
        failure = requests.exceptions.ConnectionError("temporary outage")

        with patch(
            "network_retry.requests.get", side_effect=[failure, response]
        ) as mock_get:
            with patch("network_retry.time.sleep"):
                with patch.object(price_fetcher, "USE_LIVE_PRICE", True):
                    with patch.object(
                        price_fetcher,
                        "_cache",
                        {"price": None, "timestamp": 0.0},
                    ):
                        price = price_fetcher.fetch_erg_price()

        self.assertEqual(price, 1.25)
        self.assertEqual(mock_get.call_count, 2)
        mock_get.assert_called_with(price_fetcher.COINGECKO_URL, timeout=10)


if __name__ == "__main__":
    unittest.main()
