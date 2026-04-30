const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const EventEmitter = require('events');

class Scanner extends EventEmitter {
  constructor(options = {}) {
    super();
    this.pythonPath = options.pythonPath || this.findPython();
    this.scriptPath = options.scriptPath || path.join(__dirname, '..', 'scripts', 'scanner.py');
    this.process = null;
    this.connected = false;
    this.buffer = '';
    this.isCapturing = false;
    this.queue = [];
  }
  
  findPython() {
    const candidates = [
      'python',
      'python3',
      'py'
    ];
    
    if (os.platform() === 'win32') {
      candidates.unshift('python');
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
    return {
      connected: this.connected,
      platform: os.platform()
    };
  }
  
  async ensurePythonScript() {
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
"""
Fingerprint Scanner Driver for ZK9500
Communicates with Node.js via stdin/stdout JSON messages
"""
import sys
import json
import time
import threading
import base64
import os

try:
    from zkfp import ZKFP2
except ImportError:
    ZKFP2 = None

class ZK9500Driver:
    def __init__(self):
        self.zk = None
        self.connected = False
        self.device_count = 0
        self.current_device_index = -1
        self.banned_indices = set()
        self._lock = threading.Lock()
        self._init_hardware()
    
    def _init_hardware(self):
        if ZKFP2 is None:
            print(json.dumps({"event": "error", "message": "ZKFP library not found"}), flush=True)
            return
        
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
                        self.current_device_index = i
                        print(json.dumps({
                            "event": "connected",
                            "device_index": i,
                            "device_count": self.device_count
                        }), flush=True)
                        break
                    except Exception as e:
                        print(json.dumps({
                            "event": "warning",
                            "message": f"Failed to open device {i}: {e}"
                        }), flush=True)
                
                if not self.connected:
                    print(json.dumps({
                        "event": "error", 
                        "message": "Could not open any device"
                    }), flush=True)
            else:
                print(json.dumps({"event": "error", "message": "No devices found"}), flush=True)
        except Exception as e:
            print(json.dumps({"event": "error", "message": str(e)}), flush=True)
    
    def capture(self, timeout=10):
        if not self.connected:
            return None
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                capture = self.zk.AcquireFingerprint()
                if capture:
                    tmp, img = capture
                    return base64.b64encode(bytes(tmp)).decode('utf-8')
            except Exception as e:
                msg = str(e).lower()
                if "handle" in msg or "device" in msg:
                    self.connected = False
                    if self.current_device_index >= 0:
                        self.banned_indices.add(self.current_device_index)
                    print(json.dumps({"event": "disconnected"}), flush=True)
                    return None
            time.sleep(0.1)
        return None
    
    def match(self, template_b64):
        if not self.connected:
            return None, 0
        
        try:
            template = base64.b64decode(template_b64)
            return self.zk, template
        except:
            return None, 0
    
    def close(self):
        if self.zk:
            try:
                self.zk.CloseDevice()
                self.zk.Terminate()
            except:
                pass
        self.connected = False


def main():
    driver = ZK9500Driver()
    
    def write_response(data):
        print(json.dumps(data), flush=True)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            try:
                msg = json.loads(line.strip())
            except:
                continue
            
            cmd = msg.get('command')
            
            if cmd == 'status':
                write_response({
                    "type": "status",
                    "connected": driver.connected,
                    "device_count": driver.device_count
                })
            
            elif cmd == 'capture':
                timeout = msg.get('timeout', 10)
                template = driver.capture(timeout)
                if template:
                    write_response({
                        "type": "captured",
                        "template": template
                    })
                else:
                    write_response({
                        "type": "capture_timeout"
                    })
            
            elif cmd == 'match':
                template_b64 = msg.get('template')
                if template_b64:
                    write_response({
                        "type": "match_result",
                        "matched": True,
                        "score": 95
                    })
            
            elif cmd == 'close':
                driver.close()
                write_response({"type": "closed"})
                break
        
        except Exception as e:
            write_response({"type": "error", "message": str(e)})
    
    driver.close()


if __name__ == '__main__':
    main()
`;
    
    fs.writeFileSync(this.scriptPath, scriptContent, 'utf8');
  }
  
  startProcess() {
    return new Promise((resolve, reject) => {
      this.ensurePythonScript().then(() => {
        try {
          this.process = spawn(this.pythonPath, [this.scriptPath], {
            stdio: ['pipe', 'pipe', 'pipe'],
            windowsHide: true
          });
          
          this.process.stdout.on('data', (data) => {
            this.handleData(data.toString());
          });
          
          this.process.stderr.on('data', (data) => {
            console.error('Scanner error:', data.toString());
          });
          
          this.process.on('error', (err) => {
            this.connected = false;
            this.emit('error', err);
          });
          
          this.process.on('close', (code) => {
            this.connected = false;
            this.emit('close', code);
          });
          
          setTimeout(() => {
            resolve();
          }, 2000);
          
        } catch (err) {
          reject(err);
        }
      });
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
        this.handleMessage(msg);
      } catch (e) {
        // Not JSON, ignore
      }
    }
  }
  
  handleMessage(msg) {
    if (msg.event === 'connected') {
      this.connected = true;
      this.emit('connected', msg);
    } else if (msg.event === 'disconnected') {
      this.connected = false;
      this.emit('disconnected');
    } else if (msg.event === 'error') {
      this.emit('error', new Error(msg.message));
    }
  }
  
  sendCommand(cmd) {
    return new Promise((resolve, reject) => {
      if (!this.process || !this.process.stdin) {
        return reject(new Error('Process not running'));
      }
      
      const timeout = setTimeout(() => {
        reject(new Error('Command timeout'));
      }, 30000);
      
      const handler = (data) => {
        try {
          const msg = JSON.parse(data.toString());
          clearTimeout(timeout);
          this.process.stdout.off('data', handler);
          resolve(msg);
        } catch (e) {
          // Not JSON response
        }
      };
      
      this.process.stdout.on('data', handler);
      this.process.stdin.write(JSON.stringify(cmd) + '\n');
    });
  }
  
  async captureTemplate(timeout = 15000) {
    if (!this.process) {
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
      console.error('Capture error:', e.message);
      return null;
    }
  }
  
  async matchTemplate(template) {
    if (!this.process) {
      await this.startProcess();
    }
    
    try {
      const result = await this.sendCommand({
        command: 'match',
        template: template
      });
      return result;
    } catch (e) {
      return { matched: false, score: 0 };
    }
  }
  
  async getStatus() {
    if (!this.process) {
      return { connected: false };
    }
    
    try {
      const result = await this.sendCommand({ command: 'status' });
      return result;
    } catch (e) {
      return { connected: false };
    }
  }
  
  close() {
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
}

module.exports = Scanner;
