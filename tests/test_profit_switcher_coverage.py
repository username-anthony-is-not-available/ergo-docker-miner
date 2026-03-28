import pytest
import profit_switcher
import requests
import time
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def setup_teardown():
    # Clear cache before each test
    profit_switcher._pool_score_cache = {}
    # Reset globals
    profit_switcher.last_switch_time = 0.0
    profit_switcher.start_time = time.time()
    yield

def test_get_pool_profitability_cache_hit_with_details(mocker):
    pool = profit_switcher.POOLS[0]
    mock_get = mocker.patch('profit_switcher.requests.get')

    # First call to populate cache
    mock_response = MagicMock()
    mock_response.json.return_value = {"luck": 100.0}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    profit_switcher.get_pool_profitability(pool)

    # Second call to hit cache with details
    details = profit_switcher.get_pool_profitability(pool, return_details=True)
    assert details['score'] == 0.99
    assert mock_get.call_count == 1

def test_get_pool_profitability_invalid_json(mocker):
    pool = profit_switcher.POOLS[0]
    mock_get = mocker.patch('profit_switcher.requests.get')
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    score = profit_switcher.get_pool_profitability(pool)
    assert score == 0.0

    # Try with return_details
    details = profit_switcher.get_pool_profitability(pool, return_details=True, use_cache=False)
    assert details['score'] == 0.0

def test_get_pool_profitability_2miners_formats(mocker):
    pool = profit_switcher.POOLS[0] # 2Miners
    mock_get = mocker.patch('profit_switcher.requests.get')

    # Format as list
    mock_response = MagicMock()
    mock_response.json.return_value = {"luck": [150.0]}
    mock_get.return_value = mock_response
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.99 / 1.5)

    # Format as string
    mock_response.json.return_value = {"luck": "50.0"}
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.99 / 0.5)

def test_get_pool_profitability_nanopool_formats(mocker):
    pool = profit_switcher.POOLS[2] # Nanopool
    mock_get = mocker.patch('profit_switcher.requests.get')

    # Direct luck
    mock_response = MagicMock()
    mock_response.json.return_value = {"luck": 80.0}
    mock_get.return_value = mock_response
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.99 / 0.8)

    # Data nested luck
    mock_response.json.return_value = {"data": {"luck": 120.0}}
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.99 / 1.2)

def test_get_pool_profitability_woolypooly_formats(mocker):
    pool = profit_switcher.POOLS[3] # WoolyPooly
    mock_get = mocker.patch('profit_switcher.requests.get')

    # Luck field
    mock_response = MagicMock()
    mock_response.json.return_value = {"luck": 90.0}
    mock_get.return_value = mock_response
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.991 / 0.9)

    # Effort field
    mock_response.json.return_value = {"effort": 110.0}
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.991 / 1.1)

def test_get_pool_profitability_return_details_miss(mocker):
    pool = profit_switcher.POOLS[0]
    mock_get = mocker.patch('profit_switcher.requests.get')
    mock_response = MagicMock()
    mock_response.json.return_value = {"luck": 100.0}
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    details = profit_switcher.get_pool_profitability(pool, return_details=True, use_cache=False)
    assert details['score'] == 0.99
    assert details['effort'] == 1.0
    assert details['fee'] == 0.01

def test_get_pool_profitability_parsing_error(mocker):
    pool = profit_switcher.POOLS[1] # HeroMiners
    mock_get = mocker.patch('profit_switcher.requests.get')
    mock_response = MagicMock()
    mock_response.json.return_value = {"effort_1d": "not a number"}
    mock_get.return_value = mock_response

    # Should fallback to effort 1.0
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == pytest.approx(0.991)

def test_get_pool_profitability_network_errors(mocker):
    pool = profit_switcher.POOLS[0]
    mock_get = mocker.patch('profit_switcher.requests.get')

    # RequestException
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == 0.0

    # General Exception
    mock_get.side_effect = Exception("Unexpected")
    score = profit_switcher.get_pool_profitability(pool, use_cache=False)
    assert score == 0.0

def test_main_auto_switching_disabled(mocker):
    mocker.patch('profit_switcher.read_env_file', return_value={"AUTO_PROFIT_SWITCHING": "false"})
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()

def test_main_grace_period(mocker):
    mocker.patch('profit_switcher.read_env_file', return_value={
        "AUTO_PROFIT_SWITCHING": "true",
        "MIN_SWITCH_COOLDOWN": "1000"
    })
    # Start time is recent
    profit_switcher.start_time = time.time() - 100
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()

def test_main_cooldown_period(mocker):
    mocker.patch('profit_switcher.read_env_file', return_value={
        "AUTO_PROFIT_SWITCHING": "true",
        "MIN_SWITCH_COOLDOWN": "1000"
    })
    # Runtime is long enough, but last switch was recent
    profit_switcher.start_time = time.time() - 2000
    profit_switcher.last_switch_time = time.time() - 100
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()

def test_main_custom_pool(mocker):
    profit_switcher.start_time = time.time() - 2000
    mocker.patch('profit_switcher.read_env_file', return_value={
        "AUTO_PROFIT_SWITCHING": "true",
        "POOL_ADDRESS": "stratum+tcp://custom-pool.com:1234",
        "PROFIT_SWITCHING_THRESHOLD": "0.01"
    })
    # Standard pools return 1.0
    mocker.patch('profit_switcher.get_pool_profitability', return_value=1.0)
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))

    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()

def test_main_best_pool_case(mocker):
    profit_switcher.start_time = time.time() - 2000
    mocker.patch('profit_switcher.read_env_file', return_value={
        "AUTO_PROFIT_SWITCHING": "true",
        "POOL_ADDRESS": profit_switcher.POOLS[1]["stratum"], # Herominers
        "PROFIT_SWITCHING_THRESHOLD": "0.01"
    })
    # 2Miners: 0.9, HeroMiners: 1.1, Nanopool: 1.0, WoolyPooly: 1.05
    mocker.patch('profit_switcher.get_pool_profitability', side_effect=[0.9, 1.1, 1.0, 1.05])
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))

    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()

def test_main_switching_occurs(mocker):
    profit_switcher.start_time = time.time() - 2000
    mocker.patch('profit_switcher.read_env_file', return_value={
        "AUTO_PROFIT_SWITCHING": "true",
        "POOL_ADDRESS": profit_switcher.POOLS[0]["stratum"], # 2Miners
        "PROFIT_SWITCHING_THRESHOLD": "0.01"
    })
    # 2Miners: 1.0, HeroMiners: 1.2, Nanopool: 1.0, WoolyPooly: 1.0
    mocker.patch('profit_switcher.get_pool_profitability', side_effect=[1.0, 1.2, 1.0, 1.0])
    mock_write_env = mocker.patch('profit_switcher.write_env_file')
    mock_run = mocker.patch('profit_switcher.subprocess.run')
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))

    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()

    # Assert switching side effects
    mock_write_env.assert_called_once()
    assert mock_write_env.call_args[0][0]["POOL_ADDRESS"] == profit_switcher.POOLS[1]["stratum"]
    mock_run.assert_called_once_with(["./restart.sh"], check=True)

def test_main_exception_handling(mocker):
    mocker.patch('profit_switcher.read_env_file', side_effect=Exception("Env Error"))
    mock_sleep = mocker.patch('profit_switcher.time.sleep', side_effect=Exception("Break Loop"))
    with pytest.raises(Exception, match="Break Loop"):
        profit_switcher.main()
