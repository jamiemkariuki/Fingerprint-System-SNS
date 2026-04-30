const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const EventEmitter = require('events');

class Scanner extends EventEmitter {
  constructor(options = {}) {
    super();
    this.useMock = options.mock || process.env.FP_USE_MOCK === 'true';
    this.pythonPath = options.pythonPath || this.findPython();
    this.scriptPath = options.scriptPath || path.join(__dirname, '..', 'scripts', 'scanner.py');
    this.process = null;
    this.connected = false;
    this.buffer = '';
  }

  findPython() {
    const candidates = ['python', 'python3', 'py'];

    if (os.platform() === 'win32') {
      try {
        const output = execSync('where python', { encoding: 'utf8', stdio: 'pipe' });
        return output.split('\n')[0].trim();
      } catch (e) {
        return 'python';
      }
    }

    for (const cmd of candidates) {
      try {
        execSync(`${cmd} --version`, { stdio: 'pipe' });
        return cmd;
      } catch (e) {
        continue;
      }
    }
    return 'python';
  }

  getStatus() {
    return { connected: this.connected, mock: this.useMock };
  }

  async ensurePythonScript() {
    if (this.useMock) return;

    const scriptDir = path.dirname(this.scriptPath);
    if (!fs.existsSync(scriptDir)) {
      fs.mkdirSync(scriptDir, { recursive: true });
    }

    if (!fs.existsSync(this.scriptPath)) {
      await this.createPythonScript();
    }
  }

  async createPythonScript() {
    const scriptContent = `#!/usr/bin/env python3
import sys, json, time, threading, base64, os

try:
    from zkfp import ZKFP2
except ImportError:
    ZKFP2 = None

class ZK9500Driver:
    def __init__(self):
        self.zk = None
        self.connected = False
        self.device_count = 0
        self.banned_indices = set()
        self._init_hardware()

    def _init_hardware(self):
        if ZKFP2 is None:
            print(json.dumps({"event": "error", "message": "ZKFP library not found"}), flush=True)
            return
        try:
            self.zk = ZKFP2()
            self.zk.Init()
            self.device_count = self.zk.GetDeviceCount()
            for i in range(self.device_count):
                if i in self.banned_indices: continue
                try:
                    self.zk.OpenDevice(i)
                    self.connected = True
                    print(json.dumps({"event": "connected", "device_index": i}), flush=True)
                    return
                except: pass
            print(json.dumps({"event": "error", "message": "No device available"}), flush=True)
        except Exception as e:
            print(json.dumps({"event": "error", "message": str(e)}), flush=True)

    def capture(self, timeout=10):
        if not self.connected: return None
        start = time.time()
        while time.time() - start < timeout:
            try:
                tmp, img = self.zk.AcquireFingerprint()
                return base64.b64encode(bytes(tmp)).decode('utf-8')
            except: time.sleep(0.1)
        return None

    def close(self):
        if self.zk:
            try:
                self.zk.CloseDevice()
                self.zk.Terminate()
            except: pass
        self.connected = False

driver = ZK9500Driver()

while True:
    try:
        line = sys.stdin.readline()
        if not line: break
        msg = json.loads(line.strip())
        cmd = msg.get('command')

        if cmd == 'status':
            print(json.dumps({"type": "status", "connected": driver.connected}), flush=True)

        elif cmd == 'capture':
            timeout = msg.get('timeout', 10)
            template = driver.capture(timeout)
            if template:
                print(json.dumps({"type": "captured", "template": template}), flush=True)
            else:
                print(json.dumps({"type": "capture_timeout"}), flush=True)

        elif cmd == 'close':
            driver.close()
            print(json.dumps({"type": "closed"}), flush=True)
            break

    except Exception as e:
        print(json.dumps({"type": "error", "message": str(e)}), flush=True)

driver.close()
`;
    fs.writeFileSync(this.scriptPath, scriptContent, 'utf8');
  }

  async startProcess() {
    if (this.useMock) {
      this.connected = true;
      return;
    }

    await this.ensurePythonScript();

    return new Promise((resolve, reject) => {
      try {
        this.process = spawn(this.pythonPath, [this.scriptPath], {
          stdio: ['pipe', 'pipe', 'pipe'],
          windowsHide: true
        });

        this.process.stdout.on('data', (data) => this.handleData(data.toString()));
        this.process.stderr.on('data', (data) => this.emit('error', data.toString()));
        this.process.on('error', (err) => { this.connected = false; this.emit('error', err); });
        this.process.on('close', (code) => { this.connected = false; this.emit('close', code); });

        setTimeout(resolve, 2000);
      } catch (err) {
        reject(err);
      }
    });
  }

  handleData(data) {
    this.buffer += data;
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop();

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.event === 'connected') {
          this.connected = true;
          this.emit('connected', msg);
        } else if (msg.event === 'disconnected') {
          this.connected = false;
          this.emit('disconnected');
        } else if (msg.event === 'error') {
          this.emit('error', new Error(msg.message));
        }
      } catch (e) { /* ignore */ }
    }
  }

  sendCommand(cmd) {
    return new Promise((resolve, reject) => {
      if (this.useMock) {
        resolve({ type: 'simulated', template: this.generateMockTemplate() });
        return;
      }

      if (!this.process || !this.process.stdin) {
        return reject(new Error('Scanner process not running'));
      }

      const timeout = setTimeout(() => reject(new Error('Command timeout')), 30000);

      const handler = (data) => {
        try {
          const msg = JSON.parse(data.toString());
          clearTimeout(timeout);
          this.process.stdout.off('data', handler);
          resolve(msg);
        } catch (e) { /* ignore */ }
      };

      this.process.stdout.on('data', handler);
      this.process.stdin.write(JSON.stringify(cmd) + '\n');
    });
  }

  async captureTemplate(timeout = 15000) {
    if (!this.process && !this.useMock) {
      await this.startProcess();
    }

    try {
      const result = await this.sendCommand({
        command: 'capture',
        timeout: Math.floor(timeout / 1000)
      });

      if (result.type === 'captured') {
        return result.template;
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  async close() {
    if (this.useMock) {
      this.connected = false;
      return;
    }

    if (this.process) {
      try {
        this.process.stdin.write(JSON.stringify({ command: 'close' }) + '\n');
      } catch (e) {
        this.process.kill();
      }
      this.process = null;
      this.connected = false;
    }
  }

  generateMockTemplate() {
    return 'MOCK_TEMPLATE_' + Date.now();
  }
}

module.exports = Scanner;
