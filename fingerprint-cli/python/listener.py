#!/usr/bin/env python3

import argparse
import sys
import os
import time
import logging

# Add project root to path for local zkfp module
# The zkfp module is in the parent directory of fingerprint-cli
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import psycopg

DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql://neondb_owner:npg_hnBPkldL2W9i@ep-raspy-base-akq29c7r.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require'

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USE_MOCK = os.environ.get('MOCK_SCANNER', '').lower() in ('1', 'true', 'yes')


def get_db():
    return psycopg.connect(DATABASE_URL)


# Mock scanner - exactly the same as web app
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


class FingerprintScanner:
    def __init__(self):
        self.zk = None
        self.device_count = 0
        self.is_connected = False
        self.users_cache = {}
        self.initialized = False
        self._last_init_attempt = 0
        self.current_device_index = -1
        self.banned_indices = set()
        self._init_hardware()

    def _init_hardware(self):
        # Use mock if enabled
        if USE_MOCK:
            logger.info("Using MOCK scanner (MOCK_SCANNER=1)")
            self.zk = MockZKFP()
            self.device_count = 1
            self.is_connected = True
            self.initialized = True
            return

        # Try to load ZKFP
        try:
            from zkfp import ZKFP2
        except ImportError:
            logger.warning("pyzkfp not found - using MOCK mode")
            self.zk = MockZKFP()
            self.device_count = 1
            self.is_connected = True
            self.initialized = True
            return

        # Prevent rapid re-initialization
        if (time.time() - self._last_init_attempt) < 5:
            return
        self._last_init_attempt = time.time()

        if self.is_connected:
            return

        try:
            if self.zk is None:
                self.zk = ZKFP2()
                self.zk.Init()

            self.device_count = self.zk.GetDeviceCount()
            logger.info(f"ZKFP initialized. Devices: {self.device_count}")

            if self.device_count > 0:
                if len(self.banned_indices) >= self.device_count:
                    logger.warning("All devices banned - resetting")
                    self.banned_indices.clear()

                for i in range(self.device_count):
                    if i in self.banned_indices:
                        continue
                    try:
                        logger.info(f"Trying device {i}...")
                        self.zk.OpenDevice(i)
                        self.is_connected = True
                        self.current_device_index = i
                        logger.info(f"Scanner connected (Index {i})")
                        break
                    except Exception as e:
                        logger.warning(f"Failed device {i}: {e}")

                if not self.is_connected:
                    logger.error("No devices could be opened")
        except Exception as e:
            logger.error(f"ZKFP init failed: {e}")
            self.zk = MockZKFP()
            self.is_connected = True

        self.initialized = True

    def load_users(self, users_dict):
        self.users_cache = users_dict
        logger.info(f"Loaded {len(self.users_cache)} templates")

    def capture_template(self, timeout=10):
        if not self.is_connected:
            self._init_hardware()
            if not self.is_connected:
                time.sleep(1)
                return None

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                capture = self.zk.AcquireFingerprint()
                if capture:
                    tmp, _ = capture
                    return bytes(tmp)
            except Exception as e:
                err_msg = str(e).lower()
                if 'handle' in err_msg or 'device' in err_msg:
                    logger.error(f"Scanner lost: {e}")
                    if self.current_device_index != -1:
                        self.banned_indices.add(self.current_device_index)
                    self.is_connected = False
                    self.current_device_index = -1
                    return None
                logger.error(f"Capture error: {e}")
            time.sleep(0.1)
        return None

    def match_template(self, scanned_template):
        if not self.is_connected:
            return None, 0

        best_score = 0
        best_id = None

        for uid, (name, stored_tmpl) in self.users_cache.items():
            try:
                score = self.zk.DBMatch(stored_tmpl, scanned_template)
                if score > 80 and score > best_score:
                    best_score = score
                    best_id = uid
            except Exception as e:
                logger.warning(f"Match error for user {uid}: {e}")
                continue

        return best_id, best_score

    def close(self):
        if self.zk:
            try:
                self.zk.CloseDevice()
                self.zk.Terminate()
            except:
                pass


def load_templates(conn):
    import base64
    cur = conn.cursor()
    cur.execute('SELECT id, name, fingerprint_template FROM users WHERE fingerprint_template IS NOT NULL')
    results = cur.fetchall()
    cur.close()
    # Decode base64 templates to bytes for C# DLL
    templates = {}
    for row in results:
        user_id, name, template = row
        if template:
            try:
                # Decode base64 to bytes
                template_bytes = base64.b64decode(template)
                templates[user_id] = (name, template_bytes)
            except Exception as e:
                logger.warning(f"Failed to decode template for user {user_id}: {e}")
    return templates  # {id: (name, template_bytes)}


def record_attendance(conn, user_id, user_name):
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO fingerprintlogs (user_id, timestamp, status) VALUES (%s, NOW(), %s)',
            (user_id, 'Present')
        )
        conn.commit()
        print(f"Attendance: {user_name} (ID: {user_id})")
    except Exception as e:
        logger.error(f"Record error: {e}")
    finally:
        cur.close()


def main():
    parser = argparse.ArgumentParser(description="Fingerprint Listener")
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--mock", action="store_true", help="Use mock scanner")
    args = parser.parse_args()

    print("=" * 40)
    print("Fingerprint Listener - SNS")
    print("=" * 40)
    print(f"Port: {args.port}")
    print("-" * 40)

    try:
        conn = get_db()
        print("Database connected")
    except Exception as e:
        print(f"DB failed: {e}")
        return 1

    scanner = FingerprintScanner()

    print("\nWaiting for scans...")
    print("Ctrl+C to stop\n")

    last_scan_time = {}
    SCAN_COOLDOWN = 30

    while True:
        try:
            template = scanner.capture_template(timeout=5)
            
            if template:
                try:
                    templates = load_templates(conn)
                    if not templates:
                        print("No enrolled users")
                    else:
                        scanner.load_users({uid: tmpl for uid, (_, tmpl) in templates.items()})
                        user_id, score = scanner.match_template(template)
                        
                        if user_id:
                            user_name = templates[user_id][0]
                            now = time.time()
                            last_time = last_scan_time.get(user_id, 0)
                            
                            if now - last_time > SCAN_COOLDOWN:
                                record_attendance(conn, user_id, user_name)
                                last_scan_time[user_id] = now
                            else:
                                print(f"{user_name} scanned too soon")
                        else:
                            print("No match")
                except Exception as e:
                    logger.error(f"Match error: {e}")

            time.sleep(1)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(2)

    print("\nStopped")
    conn.close()
    scanner.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())