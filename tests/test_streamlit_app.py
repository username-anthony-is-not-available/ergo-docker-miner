import unittest
from streamlit_app import format_uptime, format_host_uptime

class TestStreamlitApp(unittest.TestCase):
    def test_format_uptime(self):
        self.assertEqual(format_uptime(3661), "1h 1m 1s")
        self.assertEqual(format_uptime(0), "0h 0m 0s")
        self.assertEqual(format_uptime(3600), "1h 0m 0s")

    def test_format_host_uptime(self):
        self.assertEqual(format_host_uptime(90060), "1d 1h 1m")
        self.assertEqual(format_host_uptime(0), "0d 0h 0m")
        self.assertEqual(format_host_uptime(3600), "0d 1h 0m")

if __name__ == '__main__':
    unittest.main()
