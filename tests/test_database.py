import unittest
import os
import sqlite3
import sys
from datetime import datetime, timedelta

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Use a test database
        database.DB_FILE = 'test_miner_history.db'
        database.init_db()

    def tearDown(self):
        if os.path.exists('test_miner_history.db'):
            os.remove('test_miner_history.db')

    def test_init_db(self):
        self.assertTrue(os.path.exists('test_miner_history.db'))
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
            self.assertIsNotNone(cursor.fetchone())

            # Verify columns exist
            cursor.execute("PRAGMA table_info(history)")
            columns = [column[1] for column in cursor.fetchall()]
            self.assertIn('dual_hashrate', columns)
            self.assertIn('total_power_draw', columns)

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gpu_history'")
            self.assertIsNotNone(cursor.fetchone())

    def test_log_and_get_history(self):
        gpus = [
            {'index': 0, 'hashrate': 60.0, 'dual_hashrate': 25.0, 'temperature': 44.0, 'power_draw': 120.0, 'fan_speed': 55.0, 'accepted_shares': 50, 'rejected_shares': 1},
            {'index': 1, 'hashrate': 60.5, 'dual_hashrate': 25.5, 'temperature': 46.0, 'power_draw': 130.0, 'fan_speed': 65.0, 'accepted_shares': 50, 'rejected_shares': 1}
        ]
        database.log_history(120.5, 45.0, 60.0, 100, 2, dual_hashrate=50.5, total_power_draw=250.0, gpus=gpus)

        history = database.get_history(days=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['hashrate'], 120.5)
        self.assertEqual(history[0]['dual_hashrate'], 50.5)
        self.assertEqual(history[0]['avg_temp'], 45.0)
        self.assertEqual(history[0]['avg_fan_speed'], 60.0)
        self.assertEqual(history[0]['total_power_draw'], 250.0)
        self.assertEqual(history[0]['accepted_shares'], 100)
        self.assertEqual(history[0]['rejected_shares'], 2)

        gpu_history = database.get_gpu_history(days=1)
        self.assertEqual(len(gpu_history), 2)
        self.assertEqual(gpu_history[0]['gpu_index'], 0)
        self.assertEqual(gpu_history[0]['hashrate'], 60.0)
        self.assertEqual(gpu_history[1]['gpu_index'], 1)
        self.assertEqual(gpu_history[1]['power_draw'], 130.0)

        gpu0_history = database.get_gpu_history(gpu_index=0, days=1)
        self.assertEqual(len(gpu0_history), 1)
        self.assertEqual(gpu0_history[0]['gpu_index'], 0)

    def test_prune_history(self):
        # Insert some old data
        with database.get_connection() as conn:
            cursor = conn.cursor()
            old_time = (datetime.now() - timedelta(days=31)).isoformat()
            cursor.execute('''
                INSERT INTO history (timestamp, hashrate, dual_hashrate, avg_temp, avg_fan_speed, accepted_shares, rejected_shares)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (old_time, 100.0, 0.0, 40.0, 50.0, 50, 1))
            conn.commit()

        # Insert some new data
        database.log_history(120.5, 45.0, 60.0, 100, 2)

        history_before = database.get_history(days=40)
        self.assertEqual(len(history_before), 2)

        database.prune_history(days=30)

        history_after = database.get_history(days=40)
        self.assertEqual(len(history_after), 1)
        self.assertEqual(history_after[0]['hashrate'], 120.5)

    def test_clear_history(self):
        # Insert some data
        database.log_history(120.5, 45.0, 60.0, 100, 2)
        database.log_history(121.0, 46.0, 61.0, 105, 3)

        history_before = database.get_history(days=1)
        self.assertEqual(len(history_before), 2)

        database.clear_history()

        history_after = database.get_history(days=1)
        self.assertEqual(len(history_after), 0)

    def test_export_history_to_csv(self):
        # Insert some data
        database.log_history(120.5, 45.0, 60.0, 100, 2, total_power_draw=250.0)

        csv_file = 'test_history.csv'
        result = database.export_history_to_csv(csv_file, days=1)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(csv_file))

        import csv
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(float(rows[0]['hashrate']), 120.5)
            self.assertEqual(float(rows[0]['total_power_draw']), 250.0)

        os.remove(csv_file)

if __name__ == '__main__':
    unittest.main()
