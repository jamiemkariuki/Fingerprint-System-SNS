#!/usr/bin/env python3

import sys
import os
import time

# Add project root to path for local zkfp module
# The zkfp module is in the parent directory of fingerprint-cli
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import psycopg

DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql://neondb_owner:npg_hnBPkldL2W9i@ep-raspy-base-akq29c7r.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require'

USE_MOCK = os.environ.get('MOCK_SCANNER', '').lower() in ('1', 'true', 'yes')


def get_db():
    return psycopg.connect(DATABASE_URL)


# Mock scanner - exactly the same as listener.py
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


class Scanner:
    def __init__(self):
        self.zk = None
        self.connected = False
        self._init()
    
    def _init(self):
        if USE_MOCK:
            print("MOCK scanner mode")
            self.zk = MockZKFP()
            self.connected = True
            return
        
        try:
            from zkfp import ZKFP2
            self.zk = ZKFP2()
            self.zk.Init()
            count = self.zk.GetDeviceCount()
            if count > 0:
                self.zk.OpenDevice(0)
                self.connected = True
                print(f"Scanner connected ({count} device(s))")
            else:
                print("No scanner detected")
        except Exception as e:
            print(f"Scanner error: {e}")
            print("Using MOCK mode")
            self.zk = MockZKFP()
            self.connected = True
    
    def capture(self, timeout=15):
        print(f"Place finger on scanner... (timeout: {timeout}s)")
        
        start = time.time()
        while time.time() - start < timeout:
            if not self.connected:
                self._init()
                if not self.connected:
                    time.sleep(1)
                    continue
            
            try:
                result = self.zk.AcquireFingerprint()
                if result:
                    template, _ = result
                    print("Fingerprint captured!")
                    return bytes(template)
            except Exception as e:
                print(f"Capture error: {e}")
                self.connected = False
            
            time.sleep(0.1)
        
        return None
    
    def close(self):
        if self.zk:
            try:
                self.zk.CloseDevice()
                self.zk.Terminate()
            except:
                pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python enroll.py <student_id>")
        sys.exit(1)
    
    student_id = sys.argv[1]
    
    # Verify student exists
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM users WHERE id = %s', (student_id,))
    row = cur.fetchone()
    
    if not row:
        print(f"Student ID {student_id} not found")
        conn.close()
        sys.exit(1)
    
    student_name = row[1]
    print(f"Enrolling fingerprint for: {student_name} (ID: {student_id})")
    
    scanner = Scanner()
    template = scanner.capture()
    
    if not template:
        print("No fingerprint captured - timeout")
        scanner.close()
        conn.close()
        sys.exit(1)
    
    # Save to database (encode as base64)
    import base64
    template_b64 = base64.b64encode(template).decode('utf-8')
    cur.execute(
        'UPDATE users SET fingerprint_template = %s, fingerprint_id = %s WHERE id = %s',
        (template_b64, student_id, student_id)
    )
    conn.commit()
    print(f"Fingerprint enrolled successfully for {student_name}!")
    
    scanner.close()
    conn.close()


if __name__ == "__main__":
    main()