import unittest
import os
import time
import sys
from datetime import datetime

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import report_generator
import database

class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = 'test_data'
        os.makedirs(self.test_data_dir, exist_ok=True)
        os.environ['DATA_DIR'] = self.test_data_dir
        report_generator.DATA_DIR = self.test_data_dir
        report_generator.REPORT_FILE = os.path.join(self.test_data_dir, 'weekly_report.txt')
        database.DB_FILE = os.path.join(self.test_data_dir, 'miner_history.db')
        database.init_db()

    def tearDown(self):
        if os.path.exists(self.test_data_dir):
            import shutil
            shutil.rmtree(self.test_data_dir)

    def test_generate_weekly_report(self):
        # Insert some dummy data into the database
        now = datetime.now()
        for i in range(10):
            database.log_history(
                hashrate=100.0 + i,
                avg_temp=60.0,
                avg_fan_speed=50.0,
                accepted_shares=100,
                rejected_shares=0,
                dual_hashrate=50.0 + i,
                total_power_draw=200.0
            )

        report_generator.generate_weekly_report()
        self.assertTrue(os.path.exists(report_generator.REPORT_FILE))
        with open(report_generator.REPORT_FILE, 'r') as f:
            content = f.read()
            self.assertIn("Mining Weekly Report", content)
            self.assertIn("Average Hashrate: 104.50 MH/s", content)
            self.assertIn("Average Dual Hashrate: 54.50 MH/s", content)
            self.assertIn("Average Power Draw: 200.0 W", content)
            self.assertIn("Average Efficiency: 0.52", content)
            self.assertIn("Daily Summary:", content)

if __name__ == '__main__':
    unittest.main()
