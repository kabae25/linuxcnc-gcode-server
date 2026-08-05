import unittest
import os
import sys
import threading
import time
import socketserver

# Ensure python-api-gateway directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../python-api-gateway")))

from client import RotaryTableClient
import app

class TestRotaryTableAPI(unittest.TestCase):
    """
    Test suite for RotaryTableClient SDK operating in mock mode against RESTApiHandler server.
    """

    @classmethod
    def setUpClass(cls):
        # Enable mock mode
        app.MOCK_MODE = True
        
        # Pick an unused port for testing
        cls.port = 8899
        handler = app.RESTApiHandler

        # Allow port reuse
        socketserver.TCPServer.allow_reuse_address = True
        cls.httpd = socketserver.TCPServer(('127.0.0.1', cls.port), handler)

        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

        cls.client = RotaryTableClient(base_url=f"http://127.0.0.1:{cls.port}")
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_01_get_position(self):
        pos = self.client.get_position()
        self.assertIsInstance(pos, float)

    def test_02_move_absolute(self):
        res = self.client.move_to(360.0)
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res.get("target_position_deg"), 360.0)
        
        # Verify position updated
        pos = self.client.get_position()
        self.assertEqual(pos, 360.0)

    def test_03_move_preset(self):
        res = self.client.move_preset(180.0)
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res.get("target_position_deg"), 180.0)

        pos = self.client.get_position()
        self.assertEqual(pos, 180.0)

    def test_04_jog(self):
        # Start from 180, jog +10.0
        res = self.client.jog(direction=1, step_deg=10.0)
        self.assertEqual(res.get("status"), "ok")
        
        pos = self.client.get_position()
        self.assertEqual(pos, 190.0)

    def test_05_machine_controls(self):
        enable_res = self.client.enable()
        self.assertEqual(enable_res.get("status"), "ok")

        home_res = self.client.home()
        self.assertEqual(home_res.get("status"), "ok")

        abort_res = self.client.abort()
        self.assertEqual(abort_res.get("status"), "ok")

    def test_06_idle_module(self):
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        import rotary
        rotary.connect(f"http://127.0.0.1:{self.port}")

        rotary.move(360)
        self.assertEqual(rotary.pos(), 360.0)

        rotary.preset(90)
        self.assertEqual(rotary.pos(), 90.0)

        rotary.jog_cw(10)
        self.assertEqual(rotary.pos(), 100.0)

        rotary.jog_ccw(5)
        self.assertEqual(rotary.pos(), 95.0)

        rotary.enable()
        rotary.home()
        rotary.status()
        rotary.abort()

if __name__ == "__main__":
    unittest.main()
