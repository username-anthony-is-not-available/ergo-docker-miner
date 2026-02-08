import unittest
import os
import csv
import time
from datetime import datetime, timedelta
import report_generator
import database

class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = 'test_data'
        os.makedirs(self.test_data_dir, exist_ok=True)
        os.environ['DATA_DIR'] = self.test_data_dir
        report_generator.DATA_DIR = self.test_data_dir
        report_generator.CSV_FILE = os.path.join(self.test_data_dir, 'hashrate_history.csv')
        report_generator.REPORT_FILE = os.path.join(self.test_data_dir, 'weekly_report.txt')
        database.DB_FILE = os.path.join(self.test_data_dir, 'miner_history.db')
        database.init_db()

    def tearDown(self):
        if os.path.exists(self.test_data_dir):
            import shutil
            shutil.rmtree(self.test_data_dir)

    def test_log_to_csv(self):
        # Mock GPU_MOCK to True for get_full_miner_data
        os.environ['GPU_MOCK'] = 'true'
        report_generator.log_to_csv()

        self.assertTrue(os.path.exists(report_generator.CSV_FILE))
        with open(report_generator.CSV_FILE, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, ['timestamp', 'hashrate', 'dual_hashrate'])
            row = next(reader)
            self.assertEqual(len(row), 3)
            # Check if hashrate is a number
            float(row[1])

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

if __name__ == '__main__':
    unittest.main()
