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

            # Verify dual_hashrate column exists
            cursor.execute("PRAGMA table_info(history)")
            columns = [column[1] for column in cursor.fetchall()]
            self.assertIn('dual_hashrate', columns)

    def test_log_and_get_history(self):
        database.log_history(120.5, 45.0, 60.0, 100, 2, dual_hashrate=50.5)
        history = database.get_history(days=1)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['hashrate'], 120.5)
        self.assertEqual(history[0]['dual_hashrate'], 50.5)
        self.assertEqual(history[0]['avg_temp'], 45.0)
        self.assertEqual(history[0]['avg_fan_speed'], 60.0)
        self.assertEqual(history[0]['accepted_shares'], 100)
        self.assertEqual(history[0]['rejected_shares'], 2)

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

if __name__ == '__main__':
    unittest.main()
