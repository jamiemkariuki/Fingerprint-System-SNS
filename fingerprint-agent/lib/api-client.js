const axios = require('axios');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const path = require('path');
const fs = require('fs');
const os = require('os');

class ApiClient {
  constructor(config) {
    this.config = config;
    this.baseURL = config.serverUrl;
    this.apiKey = config.apiKey;
    this.jwtToken = null;
    this.tokenExpiry = null;
    this.offlineQueue = [];
    
    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    this.client.interceptors.request.use(async (config) => {
      if (this.jwtToken && this.tokenExpiry && Date.now() < this.tokenExpiry) {
        config.headers['Authorization'] = `Bearer ${this.jwtToken}`;
      } else if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey;
      }
      return config;
    });
    
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            await this.authenticate();
            originalRequest.headers['Authorization'] = `Bearer ${this.jwtToken}`;
            return this.client(originalRequest);
          } catch (authError) {
            this.queueRequest(originalRequest);
            throw authError;
          }
        }
        
        throw error;
      }
    );
    
    this.loadCachedToken();
  }
  
  loadCachedToken() {
    const tokenFile = path.join(os.homedir(), '.fpsns-agent', '.token');
    const expiryFile = path.join(os.homedir(), '.fpsns-agent', '.token-expiry');
    
    if (fs.existsSync(tokenFile) && fs.existsSync(expiryFile)) {
      try {
        this.jwtToken = fs.readFileSync(tokenFile, 'utf8').trim();
        this.tokenExpiry = parseInt(fs.readFileSync(expiryFile, 'utf8').trim());
        
        if (Date.now() >= this.tokenExpiry) {
          this.jwtToken = null;
          this.tokenExpiry = null;
        }
      } catch (e) {
        this.jwtToken = null;
        this.tokenExpiry = null;
      }
    }
  }
  
  saveToken() {
    const agentDir = path.join(os.homedir(), '.fpsns-agent');
    if (!fs.existsSync(agentDir)) {
      fs.mkdirSync(agentDir, { recursive: true });
    }
    
    if (this.jwtToken && this.tokenExpiry) {
      fs.writeFileSync(path.join(agentDir, '.token'), this.jwtToken);
      fs.writeFileSync(path.join(agentDir, '.token-expiry'), this.tokenExpiry.toString());
    }
  }
  
  async authenticate() {
    const payload = {
      agent_id: this.getAgentId(),
      timestamp: Date.now(),
      nonce: crypto.randomBytes(16).toString('hex')
    };
    
    const signed = jwt.sign(payload, this.apiKey, { expiresIn: '1h' });
    
    try {
      const response = await axios.post(`${this.baseURL}/sns/api/auth/token`, {
        token: signed
      }, {
        headers: {
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.data.access_token) {
        this.jwtToken = response.data.access_token;
        this.tokenExpiry = Date.now() + (response.data.expires_in || 3600000) - 60000;
        this.saveToken();
      }
    } catch (error) {
      if (error.response?.status === 401) {
        throw new Error('Authentication failed: invalid API key');
      }
      throw error;
    }
  }
  
  getAgentId() {
    const idFile = path.join(os.homedir(), '.fpsns-agent', '.agent-id');
    
    if (!fs.existsSync(idFile)) {
      const agentId = crypto.randomUUID();
      const agentDir = path.dirname(idFile);
      if (!fs.existsSync(agentDir)) {
        fs.mkdirSync(agentDir, { recursive: true });
      }
      fs.writeFileSync(idFile, agentId);
      return agentId;
    }
    
    return fs.readFileSync(idFile, 'utf8').trim();
  }
  
  queueRequest(config) {
    this.offlineQueue.push({
      url: config.url,
      method: config.method,
      data: config.data,
      timestamp: Date.now()
    });
    
    const queueFile = path.join(os.homedir(), '.fpsns-agent', '.queue');
    fs.writeFileSync(queueFile, JSON.stringify(this.offlineQueue));
  }
  
  async processQueue() {
    if (this.offlineQueue.length === 0) return;
    
    const queueFile = path.join(os.homedir(), '.fpsns-agent', '.queue');
    if (!fs.existsSync(queueFile)) return;
    
    const queue = JSON.parse(fs.readFileSync(queueFile, 'utf8'));
    const failed = [];
    
    for (const req of queue) {
      try {
        await this.client.request({
          url: req.url,
          method: req.method,
          data: req.data
        });
      } catch (e) {
        failed.push(req);
      }
    }
    
    this.offlineQueue = failed;
    fs.writeFileSync(queueFile, JSON.stringify(failed));
  }
  
  async enrollFingerprint(data) {
    try {
      const response = await this.client.post('/sns/api/fingerprint/enroll', data);
      return response.data;
    } catch (error) {
      if (error.response) {
        return { success: false, error: error.response.data.error || 'Server error' };
      }
      return { success: false, error: error.message };
    }
  }
  
  async verifyFingerprint(template) {
    try {
      const response = await this.client.post('/sns/api/fingerprint/verify', {
        template: template
      });
      return response.data;
    } catch (error) {
      if (error.response) {
        return { matched: false, error: error.response.data.error };
      }
      return { matched: false, error: error.message };
    }
  }
  
  async logAttendance(personType, personId) {
    try {
      const response = await this.client.post('/sns/api/fingerprint/log_attendance', {
        person_type: personType,
        person_id: personId
      });
      return response.data;
    } catch (error) {
      if (error.response) {
        return { success: false, error: error.response.data.error };
      }
      return { success: false, error: error.message };
    }
  }
  
  async refreshCache() {
    try {
      const response = await this.client.get('/sns/api/fingerprint/cache/refresh');
      return response.data;
    } catch (error) {
      if (error.response) {
        return { success: false, error: error.response.data.error };
      }
      return { success: false, error: error.message };
    }
  }
  
  async healthCheck() {
    try {
      const response = await this.client.get('/sns/api/fingerprint/health');
      return response.data;
    } catch (error) {
      if (error.response) {
        return { status: 'unhealthy', error: error.response.data.error };
      }
      return { status: 'unhealthy', error: error.message };
    }
  }
  
  async reconnect() {
    let attempts = 0;
    const maxAttempts = 5;
    
    while (attempts < maxAttempts) {
      try {
        const health = await this.healthCheck();
        if (health.status === 'healthy') {
          return true;
        }
      } catch (e) {
        attempts++;
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempts) * 1000));
      }
    }
    
    return false;
  }
}

module.exports = ApiClient;
