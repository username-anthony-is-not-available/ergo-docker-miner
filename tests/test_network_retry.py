import unittest
from unittest.mock import call, patch

import requests

from network_retry import RETRYABLE_STATUS_CODES, get_with_retry


TEST_URL = "https://example.invalid/status"


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"HTTP {self.status_code}", response=self
            )


class NetworkRetryTests(unittest.TestCase):
    def test_retries_transient_failures_with_exponential_backoff(self) -> None:
        success = FakeResponse(200)
        failures = [
            requests.exceptions.Timeout("read timed out"),
            FakeResponse(503),
            success,
        ]
        with patch("network_retry.requests.get", side_effect=failures) as mock_get:
            with patch("network_retry.time.sleep") as mock_sleep:
                response = get_with_retry(TEST_URL, timeout=3)

        self.assertIs(response, success)
        self.assertEqual(mock_get.call_count, 3)
        mock_get.assert_has_calls([call(TEST_URL, timeout=3)] * 3)
        mock_sleep.assert_has_calls([call(0.5), call(1.0)])
        self.assertEqual(mock_sleep.call_count, 2)

    def test_retries_every_configured_temporary_http_status(self) -> None:
        for status in sorted(RETRYABLE_STATUS_CODES):
            with self.subTest(status=status):
                success = FakeResponse(200)
                with patch(
                    "network_retry.requests.get",
                    side_effect=[FakeResponse(status), success],
                ) as mock_get:
                    with patch("network_retry.time.sleep") as mock_sleep:
                        response = get_with_retry(TEST_URL)

                self.assertIs(response, success)
                self.assertEqual(mock_get.call_count, 2)
                mock_sleep.assert_called_once_with(0.5)

    def test_does_not_retry_permanent_http_errors(self) -> None:
        for status in (400, 404, 501):
            with self.subTest(status=status):
                with patch(
                    "network_retry.requests.get", return_value=FakeResponse(status)
                ) as mock_get:
                    with patch("network_retry.time.sleep") as mock_sleep:
                        with self.assertRaises(requests.exceptions.HTTPError):
                            get_with_retry(TEST_URL)

                mock_get.assert_called_once_with(TEST_URL)
                mock_sleep.assert_not_called()

    def test_stops_after_max_attempts_without_final_sleep(self) -> None:
        connection_error = requests.exceptions.ConnectionError("unreachable")
        with patch(
            "network_retry.requests.get", side_effect=connection_error
        ) as mock_get:
            with patch("network_retry.time.sleep") as mock_sleep:
                with self.assertRaises(requests.exceptions.ConnectionError):
                    get_with_retry(TEST_URL, max_attempts=3)

        self.assertEqual(mock_get.call_count, 3)
        mock_sleep.assert_has_calls([call(0.5), call(1.0)])
        self.assertEqual(mock_sleep.call_count, 2)

    def test_rejects_invalid_retry_configuration(self) -> None:
        with patch("network_retry.requests.get") as mock_get:
            with self.assertRaises(ValueError):
                get_with_retry(TEST_URL, max_attempts=0)
            with self.assertRaises(ValueError):
                get_with_retry(TEST_URL, base_delay_seconds=-0.1)

        mock_get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
