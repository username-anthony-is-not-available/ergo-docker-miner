import logging
import subprocess
import time
from collections import deque
from collections.abc import Sequence
from typing import Any

import requests

import price_fetcher
from env_config import read_env_file, write_env_file
from network_retry import get_with_retry

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("profit_switcher")

# Cooldown and trend-smoothing settings
DEFAULT_MIN_RUNTIME = 900  # 15 minutes
DEFAULT_EMA_ALPHA = 0.35
DEFAULT_TREND_WINDOW = 6
DEFAULT_SWITCH_CONFIRMATIONS = 1

last_switch_time = 0.0
start_time = time.time()

# Cache for pool scores and historical trend tracking
_pool_score_cache: dict[str, dict[str, Any]] = {}
_pool_ema_scores: dict[str, float] = {}
_pool_score_history: dict[str, deque[float]] = {}
_candidate_pool_streaks: dict[str, int] = {}
CACHE_TTL = 300  # 5 minutes

POOLS: list[dict[str, Any]] = [
    {
        "name": "2Miners",
        "url": "https://erg.2miners.com/api/stats",
        "stratum": "stratum+tcp://erg.2miners.com:8080",
        "type": "2miners",
        "fee": 0.01,
    },
    {
        "name": "HeroMiners",
        "url": "https://ergo.herominers.com/api/stats",
        "stratum": "stratum+tcp://herominers.com:1180",
        "type": "herominers",
        "fee": 0.009,
    },
    {
        "name": "Nanopool",
        "url": "https://api.nanopool.org/v1/erg/pool/stats",
        "stratum": "stratum+tcp://erg-eu1.nanopool.org:11111",
        "type": "nanopool",
        "fee": 0.01,
    },
    {
        "name": "WoolyPooly",
        "url": "https://api.woolypooly.com/stats/ergo",
        "stratum": "stratum+tcp://pool.woolypooly.com:3100",
        "type": "woolypooly",
        "fee": 0.009,
    },
]


def reset_switcher_state() -> None:
    """Clear cached scores, EMA history, and candidate hysteresis streaks."""
    _pool_score_cache.clear()
    _pool_ema_scores.clear()
    _pool_score_history.clear()
    _candidate_pool_streaks.clear()


def compute_score_trend(history: Sequence[float]) -> float:
    """Compute a bounded normalized linear slope over recent pool scores."""
    n = len(history)
    if n < 2:
        return 0.0
    mean_y = sum(history) / n
    if mean_y <= 0:
        return 0.0

    mean_x = (n - 1) / 2.0
    numerator = sum((idx - mean_x) * (val - mean_y) for idx, val in enumerate(history))
    denominator = sum((idx - mean_x) ** 2 for idx in range(n))
    if denominator <= 0:
        return 0.0

    normalized_slope = (numerator / denominator) / mean_y
    return max(-0.25, min(0.25, normalized_slope))


def record_pool_score(
    stratum: str,
    raw_score: float,
    alpha: float = DEFAULT_EMA_ALPHA,
    window: int = DEFAULT_TREND_WINDOW,
) -> float:
    """Update EMA and recent score history for a pool, ignoring transient zero/error scores."""
    if raw_score <= 0:
        return _pool_ema_scores.get(stratum, 0.0)

    clamped_alpha = max(0.05, min(1.0, alpha))
    history = _pool_score_history.get(stratum)
    if history is None or history.maxlen != max(2, window):
        existing = list(history) if history is not None else []
        history = deque(existing[-max(2, window):], maxlen=max(2, window))
        _pool_score_history[stratum] = history
    history.append(raw_score)

    if stratum not in _pool_ema_scores:
        ema = raw_score
    else:
        ema = clamped_alpha * raw_score + (1.0 - clamped_alpha) * _pool_ema_scores[stratum]
    _pool_ema_scores[stratum] = ema

    trend = compute_score_trend(list(history))
    return ema * (1.0 + 0.1 * trend)


def get_pool_ema_score(stratum: str) -> float:
    """Return the latest smoothed EMA score for a pool stratum address."""
    return _pool_ema_scores.get(stratum, 0.0)


def get_pool_profitability(pool: dict, return_details: bool = False, use_cache: bool = True) -> Any:
    """
    Calculates a profitability score for a pool.
    Score = (1 - Fee) / Effort
    Effort is estimated from the pool API if available.
    """
    pool_url = pool["url"]

    # Check cache
    if use_cache and pool_url in _pool_score_cache:
        cache_entry = _pool_score_cache[pool_url]
        if time.time() - cache_entry['timestamp'] < CACHE_TTL:
            logger.debug(f"Using cached score for {pool['name']}")
            if return_details:
                return cache_entry['details']
            return cache_entry['score']

    try:
        response = get_with_retry(pool_url, timeout=10)
        try:
            data = response.json()
        except ValueError:
            logger.error(f"Invalid JSON response from {pool['name']} API at {pool['url']}")
            return {"score": 0.0, "effort": 1.0, "fee": pool["fee"]} if return_details else 0.0

        fee = pool["fee"]
        effort = 1.0  # Default effort (100% luck)

        try:
            if pool["type"] == "2miners":
                # 2Miners 'luck' is current round luck in percentage.
                # It can be a list or a single value depending on the exact endpoint.
                luck = data.get("luck", 100.0)
                if isinstance(luck, list) and len(luck) > 0:
                    luck = luck[0]
                if isinstance(luck, str):
                    luck = float(luck)
                effort = max(float(luck) / 100.0, 0.01)

            elif pool["type"] == "herominers":
                # HeroMiners has 'effort_1d' (average effort over 24h)
                effort = max(float(data.get("effort_1d", 1.0)), 0.01)

            elif pool["type"] == "nanopool":
                # Nanopool has 'luck' in some responses.
                luck = 100.0
                if "luck" in data:
                    luck = float(data["luck"])
                elif "data" in data and isinstance(data["data"], dict) and "luck" in data["data"]:
                    luck = float(data["data"]["luck"])
                effort = max(luck / 100.0, 0.01)

            elif pool["type"] == "woolypooly":
                # WoolyPooly 'luck' or 'effort' might be in the response.
                luck = 100.0
                if "luck" in data:
                    luck = float(data["luck"])
                elif "effort" in data:
                    luck = float(data["effort"])
                effort = max(luck / 100.0, 0.01)
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Error parsing specific stats for {pool['name']}: {e}. Falling back to default effort.")
            effort = 1.0

        score = (1.0 - fee) / effort
        erg_price = price_fetcher.fetch_erg_price()
        if erg_price is not None:
            score *= erg_price
            logger.info(f"Adjusted score with ERG price (${erg_price}): {score:.4f}")
        logger.info(f"Pool {pool['name']} analysis: Score={score:.4f}, Effort={effort:.2f}, Fee={fee:.3f}")

        # Update cache
        details = {"score": score, "effort": effort, "fee": fee}
        _pool_score_cache[pool_url] = {
            'timestamp': time.time(),
            'score': score,
            'details': details,
        }

        if return_details:
            return details
        return score
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching stats for {pool['name']}: {e}")
    except Exception as e:  # noqa: BLE001 - keep pool polling resilient to unexpected payload shapes
        logger.error(f"Unexpected error for {pool['name']}: {e}")
    return 0.0


def evaluate_switching_decision(
    raw_scores: dict[str, float],
    current_pool_address: str | None,
    threshold: float,
    required_confirmations: int = DEFAULT_SWITCH_CONFIRMATIONS,
    alpha: float = DEFAULT_EMA_ALPHA,
    window: int = DEFAULT_TREND_WINDOW,
) -> tuple[dict[str, Any] | None, float, float]:
    """Evaluate smoothed pool scores and hysteresis to decide whether to switch pools.

    Returns ``(target_pool_or_none, target_score, current_score)``.
    """
    smoothed_scores: dict[str, float] = {}
    best_pool: dict[str, Any] | None = None
    max_score = -1.0

    for pool in POOLS:
        stratum = pool["stratum"]
        smoothed = record_pool_score(stratum, raw_scores.get(stratum, 0.0), alpha=alpha, window=window)
        smoothed_scores[stratum] = smoothed
        if smoothed > max_score:
            max_score = smoothed
            best_pool = pool

    if not best_pool or best_pool["stratum"] == current_pool_address:
        _candidate_pool_streaks.clear()
        return None, max_score, smoothed_scores.get(current_pool_address or "", 0.0)

    current_pool_score = smoothed_scores.get(current_pool_address or "", 0.0)
    if current_pool_score == 0.0:
        logger.info(f"Current pool {current_pool_address} not in standard list, attempting to identify...")
        for pool in POOLS:
            if pool["stratum"] == current_pool_address:
                fetched_score = get_pool_profitability(pool)
                current_pool_score = record_pool_score(
                    pool["stratum"],
                    fetched_score,
                    alpha=alpha,
                    window=window,
                )
                logger.info(f"Matched current pool to {pool['name']}, score: {current_pool_score:.4f}")
                break

        if current_pool_score == 0.0:
            current_pool_score = 0.99
            logger.info(f"Using default score 0.99 for custom pool {current_pool_address}")

    if max_score > current_pool_score * (1 + threshold):
        candidate_stratum = best_pool["stratum"]
        streak = _candidate_pool_streaks.get(candidate_stratum, 0) + 1
        _candidate_pool_streaks.clear()
        _candidate_pool_streaks[candidate_stratum] = streak

        if streak >= max(1, required_confirmations):
            _candidate_pool_streaks.clear()
            return best_pool, max_score, current_pool_score

        logger.info(
            f"Candidate pool {best_pool['name']} ahead by >{threshold * 100:.2f}% "
            f"({streak}/{required_confirmations} confirmations). Holding current pool."
        )
        return None, max_score, current_pool_score

    _candidate_pool_streaks.clear()
    return None, max_score, current_pool_score


def main() -> None:
    global last_switch_time
    logger.info("Profit Switcher started")
    while True:
        try:
            env_vars = read_env_file()
            auto_switching = env_vars.get("AUTO_PROFIT_SWITCHING", "false").lower() == "true"
            threshold = float(env_vars.get("PROFIT_SWITCHING_THRESHOLD", "0.005"))
            interval = int(env_vars.get("PROFIT_SWITCHING_INTERVAL", "3600"))
            min_runtime_cfg = int(env_vars.get("MIN_SWITCH_COOLDOWN", DEFAULT_MIN_RUNTIME))
            ema_alpha = float(env_vars.get("PROFIT_SWITCHING_EMA_ALPHA", str(DEFAULT_EMA_ALPHA)))
            trend_window = int(env_vars.get("PROFIT_SWITCHING_TREND_WINDOW", str(DEFAULT_TREND_WINDOW)))
            confirmations = int(
                env_vars.get("PROFIT_SWITCHING_CONFIRMATIONS", str(DEFAULT_SWITCH_CONFIRMATIONS))
            )

            if not auto_switching:
                logger.info("Auto profit switching is disabled. Sleeping for 60s.")
                time.sleep(60)
                continue

            # Safety check: ensure miner has been running for a minimum duration
            current_time = time.time()
            runtime = current_time - start_time
            time_since_last_switch = current_time - last_switch_time if last_switch_time > 0 else runtime

            if runtime < min_runtime_cfg:
                logger.info(f"Miner in initial grace period ({int(runtime)}s / {min_runtime_cfg}s). Skipping check.")
                time.sleep(60)
                continue

            if time_since_last_switch < min_runtime_cfg:
                logger.info(f"Cooldown active since last switch ({int(time_since_last_switch)}s / {min_runtime_cfg}s). Skipping check.")
                time.sleep(60)
                continue

            logger.info("Auto profit switching is enabled. Checking pools...")

            current_pool_address = env_vars.get("POOL_ADDRESS")
            raw_scores: dict[str, float] = {}

            for pool in POOLS:
                raw_scores[pool["stratum"]] = get_pool_profitability(pool)

            # Log all raw scores for transparency
            scores_summary = ", ".join([f"{p['name']}: {raw_scores.get(p['stratum'], 0):.4f}" for p in POOLS])
            logger.info(f"Pool scores: {scores_summary}")

            target_pool, max_score, current_pool_score = evaluate_switching_decision(
                raw_scores=raw_scores,
                current_pool_address=current_pool_address,
                threshold=threshold,
                required_confirmations=confirmations,
                alpha=ema_alpha,
                window=trend_window,
            )

            if target_pool:
                diff_pct = (max_score / current_pool_score - 1) * 100
                logger.info(
                    f"Better pool found: {target_pool['name']} with smoothed score "
                    f"{max_score:.4f} (+{diff_pct:.2f}% over current {current_pool_score:.4f})"
                )
                logger.info(f"Switching to {target_pool['stratum']}")

                env_vars["POOL_ADDRESS"] = target_pool["stratum"]
                write_env_file(env_vars)
                last_switch_time = time.time()

                logger.info("Restarting miner...")
                subprocess.run(["./restart.sh"], check=True)
                # Wait for restart to complete and miner to stabilize
                time.sleep(300)
            else:
                logger.info("Staying on current pool.")

        except Exception as e:  # noqa: BLE001 - daemon loop must survive transient errors and retry
            logger.error(f"Error in profit switcher loop: {e}")
            interval = 60  # Retry sooner on error

        time.sleep(interval)


if __name__ == "__main__":
    main()
