import unittest
import os
import database
from datetime import datetime

class TestDatabaseEnhancements(unittest.TestCase):
    def setUp(self):
        # Use a temporary database
        os.environ['DATA_DIR'] = '.'
        if os.path.exists('miner_history.db'):
            os.remove('miner_history.db')
        database.init_db()

    def test_gpu_indices_and_history(self):
        # Log some dummy data
        gpus = [
            {'index': 0, 'hashrate': 50, 'temperature': 60, 'power_draw': 150, 'fan_speed': 40},
            {'index': 1, 'hashrate': 60, 'temperature': 65, 'power_draw': 160, 'fan_speed': 45}
        ]
        database.log_history(110, 62.5, 42.5, 10, 0, dual_hashrate=0, total_power_draw=310, gpus=gpus)

        # Check indices
        indices = database.get_gpu_indices()
        self.assertEqual(indices, [0, 1])

        # Check history for GPU 0
        history0 = database.get_gpu_history(gpu_index=0)
        self.assertEqual(len(history0), 1)
        self.assertEqual(history0[0]['hashrate'], 50)

        # Check history for GPU 1
        history1 = database.get_gpu_history(gpu_index=1)
        self.assertEqual(len(history1), 1)
        self.assertEqual(history1[0]['hashrate'], 60)

    def tearDown(self):
        if os.path.exists('miner_history.db'):
            os.remove('miner_history.db')

if __name__ == '__main__':
    unittest.main()
