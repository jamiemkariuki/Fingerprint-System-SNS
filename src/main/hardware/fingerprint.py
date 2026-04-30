import time
import threading
import logging
import os

try:
    from zkfp import ZKFP2
except ImportError:
    ZKFP2 = None

logger = logging.getLogger(__name__)

USE_MOCK = os.getenv("MOCK_SCANNER", "").lower() in ("1", "true", "yes")


# Mock scanner for testing without hardware
class MockZKFP:
    def __init__(self):
        self.device_count = 1
        self.connected = False

    def Init(self):
        return True

    def GetDeviceCount(self):
        return 1

    def OpenDevice(self, index=0):
        self.connected = True
        return True

    def AcquireFingerprint(self):
        time.sleep(0.5)
        import random

        template = bytes([random.randint(0, 255) for _ in range(512)])
        image = bytes([random.randint(0, 255) for _ in range(25600)])
        return (template, image)

    def DBMatch(self, template1, template2):
        if template1 == template2:
            return 100
        return 0

    def CloseDevice(self):
        self.connected = False

    def Terminate(self):
        pass


# Singleton simulation for module-level access
_scanner_instance = None
_lock = threading.Lock()


class FingerprintScanner:
    def __init__(self):
        self.zk = None
        self.device_count = 0
        self.is_connected = False
        self.users_cache = {}  # {db_id: template_bytes}
        self.initialized = False
        self._last_init_attempt = 0
        self.current_device_index = -1
        self.banned_indices = set()
        self._init_hardware()

    def _init_hardware(self):
        # Use mock scanner if enabled
        if USE_MOCK:
            logger.info("Using MOCK scanner (MOCK_SCANNER=1)")
            self.zk = MockZKFP()
            self.device_count = 1
            self.is_connected = True
            self.initialized = True
            return

        # Prevent rapid re-initialization attempts (Backoff Strategy)
        if (time.time() - self._last_init_attempt) < 5:
            return

        self._last_init_attempt = time.time()

        # If we are already connected, verify it's still alive, otherwise reset
        if self.is_connected:
            return

        if ZKFP2:
            try:
                # Only re-instantiate if null
                if self.zk is None:
                    self.zk = ZKFP2()
                    self.zk.Init()

                self.device_count = self.zk.GetDeviceCount()
                logger.info(f"ZKFP initialized. Devices found: {self.device_count}")

                if self.device_count > 0:
                    # If all devices are banned, reset the ban list to try again
                    if len(self.banned_indices) >= self.device_count:
                        logger.warning(
                            "All devices were banned. Resetting ban list to retry."
                        )
                        self.banned_indices.clear()

                    # Try to open available devices until one works
                    for i in range(self.device_count):
                        if i in self.banned_indices:
                            logger.info(f"Skipping banned device index {i}")
                            continue

                        try:
                            logger.info(f"Attempting to open device index {i}...")
                            self.zk.OpenDevice(i)
                            self.is_connected = True
                            self.current_device_index = i
                            logger.info(f"Successfully opened ZK9500 (Index {i})")
                            break
                        except Exception as open_err:
                            logger.warning(f"Failed to open device {i}: {open_err}")

                    if not self.is_connected:
                        logger.error("Could not open any detected devices.")
            except Exception as e:
                logger.error(f"ZKFP Initialization/Connection failed: {e}")
                # If Init failed, maybe we need to recreate the object next time
                self.zk = None
        else:
            if not self.initialized:  # Log once
                logger.warning("ZKFP library not found. Running in MOCK mode.")
            self.initialized = (
                True  # Mark as "initialized" so we don't spam mock warning
            )

    def load_users(self, users_dict):
        """
        Load users into memory for fast matching.
        users_dict: { id: template_bytes }
        """
        with _lock:
            self.users_cache = users_dict
            logger.info(f"Loaded {len(self.users_cache)} templates into memory.")

    def capture_template(self, timeout=10):
        """
        Waits for a finger and returns the template bytes.
        Blocking call with timeout.
        """
        if not self.is_connected:
            # Try to reconnect if not connected
            self._init_hardware()
            if not self.is_connected:
                time.sleep(1)
                return None

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                capture = self.zk.AcquireFingerprint()
                if capture:
                    tmp, img = capture
                    return bytes(tmp)
            except Exception as e:
                # If handle is invalid or device disconnected, mark as not connected
                err_msg = str(e).lower()
                if "handle" in err_msg or "device" in err_msg:
                    logger.error(f"Hardware connection lost: {e}")

                    # Mark this specific index as bad so we don't pick it again immediately
                    if self.current_device_index != -1:
                        logger.warning(
                            f"Banning device index {self.current_device_index} due to error."
                        )
                        self.banned_indices.add(self.current_device_index)

                    self.is_connected = False
                    self.current_device_index = -1
                    return None

                # For other errors (glitches), just log and continue
                logger.error(f"Capture error: {e}")
                time.sleep(1)
            time.sleep(0.1)
        return None

    def match_template(self, scanned_template):
        """
        Matches a scanned template against the loaded cache.
        Returns: (best_id, score) or (None, 0)
        """
        if not self.is_connected:
            return None, 0

        best_score = 0
        best_id = None

        with _lock:
            # We iterate over a copy of items to avoid runtime errors if cache changes
            for uid, stored_tmpl in list(self.users_cache.items()):
                try:
                    score = self.zk.DBMatch(stored_tmpl, scanned_template)
                    if score > 80 and score > best_score:
                        best_score = score
                        best_id = uid
                except:
                    continue

        return best_id, best_score

    def close(self):
        if self.zk:
            try:
                self.zk.CloseDevice()
                self.zk.Terminate()
            except:
                pass


# Global instance
def get_scanner():
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = FingerprintScanner()
    return _scanner_instance


# Wrapper functions to maintain some compatibility or easy access
def enroll_fingerprint(db_id=None):
    """
    Captures a fingerprint and returns the template bytes.
    Note: The original app expected an ID returned.
    Here we return the TEMPLATE (bytes) so the caller can save it to DB.
    """
    scanner = get_scanner()
    logger.info("Starting enrollment capture...")
    template = scanner.capture_template(timeout=15)
    if template:
        logger.info("Enrollment capture successful.")
        return template
    logger.warning("Enrollment capture timed out.")
    return None


# Export 'finger'-like object if needed, but we prefer direct usage
finger = get_scanner()
