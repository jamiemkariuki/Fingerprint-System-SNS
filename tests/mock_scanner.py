"""
Mock Fingerprint Scanner for Testing
Simulates ZK9500 scanner without hardware
"""

import time
import random
import base64
import threading
import logging

logger = logging.getLogger(__name__)

MOCK_TEMPLATES = {}


class MockZKFP2:
    def __init__(self):
        self.connected = False
        self.device_count = 1

    def Init(self):
        logger.info("Mock ZKFP2 initialized")
        return True

    def GetDeviceCount(self):
        return 1

    def OpenDevice(self, index=0):
        self.connected = True
        logger.info(f"Mock device {index} opened")
        return True

    def AcquireFingerprint(self):
        time.sleep(0.5)
        template = bytes([random.randint(0, 255) for _ in range(512)])
        image = bytes([random.randint(0, 255) for _ in range(25600)])
        return (template, image)

    def DBMatch(self, template1, template2):
        if template1 == template2:
            return 100
        return random.randint(0, 30)

    def CloseDevice(self):
        self.connected = False

    def Terminate(self):
        pass


def create_mock_scanner():
    """Create a mock scanner instance"""
    return MockZKFP2()


class MockFingerprintScanner:
    def __init__(self):
        self.zk = create_mock_scanner()
        self.is_connected = False
        self.users_cache = {}
        self.initialized = False
        self.current_device_index = 0
        self._connect()

    def _connect(self):
        try:
            self.zk.OpenDevice(0)
            self.is_connected = True
            logger.info("Mock scanner connected")
        except Exception as e:
            logger.error(f"Mock scanner connection failed: {e}")

    def load_users(self, users_dict):
        self.users_cache = users_dict
        logger.info(f"Mock loaded {len(users_dict)} templates")

    def capture_template(self, timeout=10):
        if not self.is_connected:
            self._connect()

        start = time.time()
        while time.time() - start < timeout:
            if self.is_connected:
                capture = self.zk.AcquireFingerprint()
                if capture:
                    template, _ = capture
                    return bytes(template)
            time.sleep(0.1)
        return None

    def match_template(self, scanned_template):
        if not self.is_connected:
            return None, 0

        best_score = 0
        best_id = None

        for uid, stored_tmpl in self.users_cache.items():
            try:
                score = self.zk.DBMatch(stored_tmpl, scanned_template)
                if score > 80 and score > best_score:
                    best_score = score
                    best_id = uid
            except:
                continue

        return best_id, best_score

    def close(self):
        self.zk.CloseDevice()
        self.is_connected = False


_mock_instance = None
_lock = threading.Lock()


def get_scanner():
    global _mock_instance
    if _mock_instance is None:
        with _lock:
            if _mock_instance is None:
                _mock_instance = MockFingerprintScanner()
    return _mock_instance
