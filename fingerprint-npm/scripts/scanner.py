#!/usr/bin/env python3
"""
Fingerprint Scanner Driver for ZK9500
Communicates with Node.js via stdin/stdout JSON messages
"""

import sys
import json
import time

try:
    from zkfp import ZKFP2
except ImportError:
    ZKFP2 = None


class MockScanner:
    """Mock scanner for testing without hardware"""

    def __init__(self):
        self.counter = 0

    def capture(self, timeout=10):
        self.counter += 1
        # Simulate capture delay
        time.sleep(min(2, timeout / 10))
        # Return a mock template
        import base64

        return base64.b64encode(
            f"MOCK_TEMPLATE_{self.counter}_{time.time()}".encode()
        ).decode()


class ZK9500Driver:
    def __init__(self):
        self.zk = None
        self.connected = False
        self.device_count = 0
        self.mock = ZKFP2 is None
        self.banned_indices = set()

        if self.mock:
            print(json.dumps({"event": "connected", "mock": True}), flush=True)
            self.connected = True
        else:
            self._init_hardware()

    def _init_hardware(self):
        try:
            self.zk = ZKFP2()
            self.zk.Init()
            self.device_count = self.zk.GetDeviceCount()

            if self.device_count > 0:
                for i in range(self.device_count):
                    if i in self.banned_indices:
                        continue
                    try:
                        self.zk.OpenDevice(i)
                        self.connected = True
                        print(
                            json.dumps({"event": "connected", "device_index": i}),
                            flush=True,
                        )
                        return
                    except Exception as e:
                        print(
                            json.dumps(
                                {"event": "warning", "message": f"Device {i}: {e}"}
                            ),
                            flush=True,
                        )
                print(
                    json.dumps({"event": "error", "message": "No device available"}),
                    flush=True,
                )
            else:
                print(
                    json.dumps({"event": "error", "message": "No devices found"}),
                    flush=True,
                )
        except Exception as e:
            print(json.dumps({"event": "error", "message": str(e)}), flush=True)

    def capture(self, timeout=10):
        if self.mock:
            return MockScanner().capture(timeout)

        if not self.connected:
            return None
        start = time.time()
        while time.time() - start < timeout:
            try:
                tmp, img = self.zk.AcquireFingerprint()
                import base64

                return base64.b64encode(bytes(tmp)).decode("utf-8")
            except Exception as e:
                msg = str(e).lower()
                if "handle" in msg or "device" in msg:
                    self.connected = False
                    print(json.dumps({"event": "disconnected"}), flush=True)
                    return None
                time.sleep(0.1)
        return None

    def close(self):
        if self.zk:
            try:
                self.zk.CloseDevice()
                self.zk.Terminate()
            except:
                pass
        self.connected = False


driver = ZK9500Driver()

while True:
    try:
        line = sys.stdin.readline()
        if not line:
            break
        msg = json.loads(line.strip())
        cmd = msg.get("command")

        if cmd == "status":
            print(
                json.dumps(
                    {
                        "type": "status",
                        "connected": driver.connected,
                        "mock": driver.mock,
                    }
                ),
                flush=True,
            )

        elif cmd == "capture":
            timeout = msg.get("timeout", 10)
            template = driver.capture(timeout)
            if template:
                print(
                    json.dumps({"type": "captured", "template": template}), flush=True
                )
            else:
                print(json.dumps({"type": "capture_timeout"}), flush=True)

        elif cmd == "close":
            driver.close()
            print(json.dumps({"type": "closed"}), flush=True)
            break

    except Exception as e:
        print(json.dumps({"type": "error", "message": str(e)}), flush=True)

driver.close()
