import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import time

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import metrics
from metrics import update_metrics

class TestTelegramNotifications(unittest.TestCase):
    def setUp(self):
        # Reset state
        metrics.unhealthy_since = None
        metrics.is_currently_notified = False
        metrics.TELEGRAM_ENABLE = True
        metrics.TELEGRAM_BOT_TOKEN = "fake_token"
        metrics.TELEGRAM_CHAT_ID = "fake_chat_id"
        metrics.TELEGRAM_NOTIFY_THRESHOLD = 10 # 10 seconds for testing

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.send_telegram_notification')
    @patch('metrics.get_full_miner_data')
    def test_notification_sent_after_threshold(self, mock_full_data, mock_send, mock_prune, mock_log):
        # Rig is down
        mock_full_data.return_value = None

        # Mock time to be stable
        start_time = 1000000.0
        with patch('time.time', return_value=start_time):
            # First check: mark unhealthy
            update_metrics()
            self.assertEqual(metrics.unhealthy_since, start_time)
            mock_send.assert_not_called()

        # Second check: Fast forward time past threshold
        with patch('time.time', return_value=start_time + 15):
            update_metrics()
            mock_send.assert_called_once()
            self.assertTrue(metrics.is_currently_notified)

            # Check reason in message
            args, _ = mock_send.call_args
            self.assertIn("API Unreachable", args[0])
            self.assertIn("Duration: 15s", args[0])

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.send_telegram_notification')
    @patch('metrics.get_full_miner_data')
    def test_notification_recovery(self, mock_full_data, mock_send, mock_prune, mock_log):
        # Set state to notified
        metrics.unhealthy_since = 1000000.0 - 20
        metrics.is_currently_notified = True

        # Rig recovered
        mock_full_data.return_value = {
            'total_hashrate': 100.5,
            'status': 'Mining',
            'total_dual_hashrate': 0,
            'avg_fan_speed': 50,
            'total_power_draw': 200,
            'total_accepted_shares': 10,
            'total_rejected_shares': 0,
            'avg_temperature': 60,
            'gpus': []
        }

        update_metrics()

        # Recovery message should be sent
        mock_send.assert_called_once()
        self.assertIn("RECOVERED", mock_send.call_args[0][0])
        self.assertIn("Hashrate: 100.5 MH/s", mock_send.call_args[0][0])
        self.assertFalse(metrics.is_currently_notified)
        self.assertIsNone(metrics.unhealthy_since)

    @patch('database.log_history')
    @patch('database.prune_history')
    @patch('metrics.send_telegram_notification')
    @patch('metrics.get_full_miner_data')
    def test_zero_hashrate_notification(self, mock_full_data, mock_send, mock_prune, mock_log):
        # Rig is up but 0 hashrate
        mock_full_data.return_value = {
            'total_hashrate': 0,
            'status': 'Idle',
            'total_dual_hashrate': 0,
            'avg_fan_speed': 50,
            'total_power_draw': 200,
            'total_accepted_shares': 10,
            'total_rejected_shares': 0,
            'avg_temperature': 60,
            'gpus': []
        }

        start_time = 1000000.0
        with patch('time.time', return_value=start_time):
            # First check
            update_metrics()
            self.assertEqual(metrics.unhealthy_since, start_time)

        # Fast forward
        with patch('time.time', return_value=start_time + 15):
            update_metrics()
            mock_send.assert_called_once()
            self.assertIn("Zero Hashrate", mock_send.call_args[0][0])

    @patch('requests.post')
    def test_send_telegram_notification_actual_call(self, mock_post):
        metrics.TELEGRAM_ENABLE = True
        metrics.TELEGRAM_BOT_TOKEN = "test_token"
        metrics.TELEGRAM_CHAT_ID = "test_chat"

        from metrics import send_telegram_notification

        # Success case
        mock_post.return_value.raise_for_status = MagicMock()
        send_telegram_notification("Test message")

        mock_post.assert_called_once()
        url = mock_post.call_args[0][0]
        self.assertIn("test_token", url)
        json_data = mock_post.call_args[1]['json']
        self.assertEqual(json_data['chat_id'], "test_chat")
        self.assertEqual(json_data['text'], "Test message")

    @patch('requests.post')
    def test_send_telegram_notification_disabled(self, mock_post):
        metrics.TELEGRAM_ENABLE = False
        from metrics import send_telegram_notification
        send_telegram_notification("Test message")
        mock_post.assert_not_called()

if __name__ == '__main__':
    unittest.main()
