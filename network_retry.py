"""Bounded retry behavior for idempotent HTTP GET requests."""

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _is_retryable(error: requests.exceptions.RequestException) -> bool:
    if isinstance(
        error,
        (requests.exceptions.ConnectionError, requests.exceptions.Timeout),
    ):
        return True
    if isinstance(error, requests.exceptions.HTTPError):
        response = error.response
        return response is not None and response.status_code in RETRYABLE_STATUS_CODES
    return False


def get_with_retry(
    url: str,
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.5,
    **kwargs: Any,
) -> requests.Response:
    """Make a GET request, retrying transient failures with exponential backoff."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if base_delay_seconds < 0:
        raise ValueError("base_delay_seconds cannot be negative")

    for attempt in range(max_attempts):
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as error:
            if not _is_retryable(error) or attempt + 1 == max_attempts:
                raise

            delay = base_delay_seconds * (2**attempt)
            logger.warning(
                "Transient GET failure (%s) on attempt %d/%d; retrying in %.2fs",
                type(error).__name__,
                attempt + 1,
                max_attempts,
                delay,
            )
            time.sleep(delay)

    raise RuntimeError("GET retry loop exited without a result")
