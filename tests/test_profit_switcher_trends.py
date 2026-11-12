import pytest

import profit_switcher
from config_validator import validate_configuration


@pytest.fixture(autouse=True)
def clean_profit_switcher_state() -> None:
    profit_switcher.reset_switcher_state()


def test_compute_score_trend_positive_negative_and_bounded() -> None:
    assert profit_switcher.compute_score_trend([]) == 0.0
    assert profit_switcher.compute_score_trend([1.0]) == 0.0

    rising = profit_switcher.compute_score_trend([1.0, 1.1, 1.2, 1.3])
    falling = profit_switcher.compute_score_trend([1.3, 1.2, 1.1, 1.0])
    extreme = profit_switcher.compute_score_trend([0.01, 100.0])

    assert rising > 0
    assert falling < 0
    assert extreme <= 0.25


def test_record_pool_score_smooths_transient_spike_and_ignores_zeros() -> None:
    stratum = profit_switcher.POOLS[0]["stratum"]

    s1 = profit_switcher.record_pool_score(stratum, 1.0, alpha=0.35, window=6)
    s2 = profit_switcher.record_pool_score(stratum, 1.0, alpha=0.35, window=6)
    # Single large spike should be damped well below raw 2.0
    s3 = profit_switcher.record_pool_score(stratum, 2.0, alpha=0.35, window=6)
    # Zero/API error score should preserve prior EMA instead of crashing to 0
    s4 = profit_switcher.record_pool_score(stratum, 0.0, alpha=0.35, window=6)

    assert s1 == pytest.approx(1.0)
    assert s2 == pytest.approx(1.0)
    assert 1.3 < s3 < 1.5
    assert s4 == pytest.approx(profit_switcher.get_pool_ema_score(stratum))
    assert s4 > 1.0


def test_evaluate_switching_decision_requires_consecutive_confirmations() -> None:
    current = profit_switcher.POOLS[0]["stratum"]
    candidate = profit_switcher.POOLS[1]["stratum"]
    other_1 = profit_switcher.POOLS[2]["stratum"]
    other_2 = profit_switcher.POOLS[3]["stratum"]

    scores = {
        current: 1.0,
        candidate: 1.25,
        other_1: 0.9,
        other_2: 0.9,
    }

    # First interval: candidate is ahead, but confirmations=2 holds the switch
    target, _, _ = profit_switcher.evaluate_switching_decision(
        raw_scores=scores,
        current_pool_address=current,
        threshold=0.05,
        required_confirmations=2,
    )
    assert target is None

    # Second consecutive interval: candidate remains ahead -> switch approved
    target, _, _ = profit_switcher.evaluate_switching_decision(
        raw_scores=scores,
        current_pool_address=current,
        threshold=0.05,
        required_confirmations=2,
    )
    assert target is not None
    assert target["stratum"] == candidate


def test_evaluate_switching_decision_resets_streak_when_spike_subsides() -> None:
    current = profit_switcher.POOLS[0]["stratum"]
    candidate = profit_switcher.POOLS[1]["stratum"]
    other_1 = profit_switcher.POOLS[2]["stratum"]
    other_2 = profit_switcher.POOLS[3]["stratum"]

    # Interval 1: spike on candidate
    target, _, _ = profit_switcher.evaluate_switching_decision(
        raw_scores={current: 1.0, candidate: 1.3, other_1: 0.9, other_2: 0.9},
        current_pool_address=current,
        threshold=0.05,
        required_confirmations=2,
    )
    assert target is None

    # Interval 2: current recovers -> streak resets
    target, _, _ = profit_switcher.evaluate_switching_decision(
        raw_scores={current: 1.4, candidate: 1.0, other_1: 0.9, other_2: 0.9},
        current_pool_address=current,
        threshold=0.05,
        required_confirmations=2,
    )
    assert target is None

    # Interval 3: candidate ahead again, streak starts back at 1/2 -> still holds
    target, _, _ = profit_switcher.evaluate_switching_decision(
        raw_scores={current: 1.0, candidate: 1.5, other_1: 0.9, other_2: 0.9},
        current_pool_address=current,
        threshold=0.05,
        required_confirmations=2,
    )
    assert target is None


def test_config_validator_validates_profit_switching_trend_settings() -> None:
    base = {
        "MINER": "lolminer",
        "POOL_ADDRESS": "stratum+tcp://erg.2miners.com:8080",
        "WALLET_ADDRESS": "sample-wallet",
        "PROFIT_SWITCHING_EMA_ALPHA": "0.35",
        "PROFIT_SWITCHING_TREND_WINDOW": "6",
        "PROFIT_SWITCHING_CONFIRMATIONS": "2",
    }
    assert validate_configuration(base, "missing.json") == []

    invalid = dict(base)
    invalid["PROFIT_SWITCHING_EMA_ALPHA"] = "1.5"
    invalid["PROFIT_SWITCHING_TREND_WINDOW"] = "1"
    invalid["PROFIT_SWITCHING_CONFIRMATIONS"] = "0"

    errors = validate_configuration(invalid, "missing.json")
    assert len(errors) == 3
