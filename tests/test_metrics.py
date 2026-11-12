import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import metrics
from metrics import (
    API_LATENCY,
    API_UP,
    AVG_FAN_SPEED,
    AVG_POWER_DRAW,
    AVG_TEMPERATURE,
    DUAL_HASHRATE,
    GPU_HASHRATE,
    GPU_POWER_DRAW,
    GPU_TEMPERATURE,
    HASHRATE,
    INFO,
    MAX_GPU_TEMPERATURE,
    NODE_LATENCY,
    POOL_LATENCY,
    POOL_UP,
    TOTAL_POWER_DRAW,
    TOTAL_SHARES_ACCEPTED,
    TOTAL_SHARES_REJECTED,
    UPTIME,
    WORKER,
    measure_pool_latency,
    update_metrics,
)


class TestMetrics(unittest.TestCase):
    def setUp(self):
        metrics.last_prune_time = 0
        # Reset Prometheus metrics
        HASHRATE.labels(worker=WORKER).set(0)
        DUAL_HASHRATE.labels(worker=WORKER).set(0)
        AVG_TEMPERATURE.labels(worker=WORKER).set(0)
        MAX_GPU_TEMPERATURE.labels(worker=WORKER).set(0)
        AVG_FAN_SPEED.labels(worker=WORKER).set(0)
        TOTAL_POWER_DRAW.labels(worker=WORKER).set(0)
        AVG_POWER_DRAW.labels(worker=WORKER).set(0)
        TOTAL_SHARES_ACCEPTED.labels(worker=WORKER).set(0)
        TOTAL_SHARES_REJECTED.labels(worker=WORKER).set(0)
        API_UP.labels(worker=WORKER).set(0)
        UPTIME.labels(worker=WORKER).set(0)
        API_LATENCY.labels(worker=WORKER).set(0)
        NODE_LATENCY.labels(worker=WORKER).set(0)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_full_miner_data')
    def test_update_metrics_consolidated(self, mock_full_data, mock_prune, mock_log):
        mock_full_data.return_value = {
            'miner': 'lolminer',
            'total_hashrate': 120.5,
            'total_dual_hashrate': 250.5,
            'total_power_draw': 245.5,
            'avg_temperature': 37.5,
            'avg_fan_speed': 57.5,
            'total_accepted_shares': 210,
            'total_rejected_shares': 5,
            'status': 'Mining',
            'driver_version': '535',
            'miner_instances': {'4444': 'UP', '4445': 'DOWN'},
            'gpus': [
                {
                    'index': 0, 'hashrate': 60.2, 'dual_hashrate': 125.2, 'fan_speed': 55,
                    'accepted_shares': 100, 'rejected_shares': 2, 'temperature': 35.0, 'power_draw': 120.5
                },
                {
                    'index': 1, 'hashrate': 60.3, 'dual_hashrate': 125.3, 'fan_speed': 60,
                    'accepted_shares': 110, 'rejected_shares': 3, 'temperature': 40.0, 'power_draw': 125.0
                }
            ]
        }

        update_metrics()

        # Assert global metrics
        self.assertEqual(HASHRATE.labels(worker=WORKER)._value.get(), 120.5)
        self.assertEqual(DUAL_HASHRATE.labels(worker=WORKER)._value.get(), 250.5)
        self.assertEqual(AVG_TEMPERATURE.labels(worker=WORKER)._value.get(), 37.5)
        self.assertEqual(MAX_GPU_TEMPERATURE.labels(worker=WORKER)._value.get(), 40.0)
        self.assertEqual(TOTAL_POWER_DRAW.labels(worker=WORKER)._value.get(), 245.5)
        self.assertEqual(AVG_POWER_DRAW.labels(worker=WORKER)._value.get(), 122.75)
        self.assertEqual(AVG_FAN_SPEED.labels(worker=WORKER)._value.get(), 57.5)
        self.assertEqual(TOTAL_SHARES_ACCEPTED.labels(worker=WORKER)._value.get(), 210)
        self.assertEqual(TOTAL_SHARES_REJECTED.labels(worker=WORKER)._value.get(), 5)
        self.assertEqual(API_UP.labels(worker=WORKER)._value.get(), 1)
        self.assertEqual(UPTIME.labels(worker=WORKER)._value.get(), 0) # Mock uptime is 0 unless specified
        self.assertGreaterEqual(API_LATENCY.labels(worker=WORKER)._value.get(), 0.0)
        self.assertGreaterEqual(NODE_LATENCY.labels(worker=WORKER)._value.get(), 0.0)

        # Assert individual instance metrics
        self.assertEqual(metrics.MINER_INSTANCE_UP.labels(port="4444", worker=WORKER)._value.get(), 1)
        self.assertEqual(metrics.MINER_INSTANCE_UP.labels(port="4445", worker=WORKER)._value.get(), 0)

        # Assert info metric
        self.assertEqual(INFO.labels(miner=metrics.MINER_TYPE, version=metrics.MINER_VERSION, worker=WORKER, driver='535')._value.get(), 1)

        # Assert GPU metrics
        self.assertEqual(GPU_HASHRATE.labels(gpu="0", worker=WORKER)._value.get(), 60.2)
        self.assertEqual(GPU_TEMPERATURE.labels(gpu="0", worker=WORKER)._value.get(), 35.0)
        self.assertEqual(GPU_POWER_DRAW.labels(gpu="0", worker=WORKER)._value.get(), 120.5)

        # Assert database calls
        mock_log.assert_called_once_with(
            120.5, 37.5, 57.5, 210, 5, 250.5, 245.5, mock_full_data.return_value['gpus']
        )
        mock_prune.assert_called_once()

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.get_full_miner_data')
    def test_api_error(self, mock_full_data, mock_prune, mock_log):
        mock_full_data.return_value = None

        update_metrics()

        self.assertEqual(HASHRATE.labels(worker=WORKER)._value.get(), 0)
        self.assertEqual(AVG_TEMPERATURE.labels(worker=WORKER)._value.get(), 0)
        self.assertEqual(MAX_GPU_TEMPERATURE.labels(worker=WORKER)._value.get(), 0)
        self.assertEqual(TOTAL_POWER_DRAW.labels(worker=WORKER)._value.get(), 0)
        self.assertEqual(AVG_POWER_DRAW.labels(worker=WORKER)._value.get(), 0)
        self.assertEqual(API_UP.labels(worker=WORKER)._value.get(), 0)
        mock_log.assert_not_called()

    @patch('metrics.socket.create_connection')
    def test_measure_pool_latency_success_and_failure(self, mock_connect):
        mock_sock = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_sock

        latency = measure_pool_latency('stratum+tcp://erg.2miners.com:8080', timeout=1.5)
        self.assertIsNotNone(latency)
        self.assertGreaterEqual(latency, 0.0)
        mock_connect.assert_called_once_with(('erg.2miners.com', 8080), timeout=1.5)

        mock_connect.side_effect = OSError('connection timed out')
        self.assertIsNone(measure_pool_latency('stratum+tcp://erg.2miners.com:8080'))
        self.assertIsNone(measure_pool_latency('not-a-valid-pool'))

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.measure_pool_latency')
    @patch('metrics.get_full_miner_data')
    def test_update_metrics_records_pool_latency_and_up(
        self, mock_full_data, mock_pool_latency, mock_prune, mock_log
    ):
        mock_full_data.return_value = None
        pool_url = 'stratum+tcp://erg.2miners.com:8080'

        with patch.dict(os.environ, {'POOL_ADDRESS': pool_url}):
            mock_pool_latency.return_value = 0.042
            update_metrics()
            self.assertEqual(POOL_UP.labels(pool=pool_url, worker=WORKER)._value.get(), 1)
            self.assertAlmostEqual(POOL_LATENCY.labels(pool=pool_url, worker=WORKER)._value.get(), 0.042)

            mock_pool_latency.return_value = None
            update_metrics()
            self.assertEqual(POOL_UP.labels(pool=pool_url, worker=WORKER)._value.get(), 0)

if __name__ == '__main__':
    unittest.main()
