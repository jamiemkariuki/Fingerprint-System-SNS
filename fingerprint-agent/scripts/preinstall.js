const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('Installing @fpsns/agent...');

const agentDir = path.join(os.homedir(), '.fpsns-agent');

if (!fs.existsSync(agentDir)) {
  fs.mkdirSync(agentDir, { recursive: true });
  console.log(`Created config directory: ${agentDir}`);
}

const envFile = path.join(agentDir, '.env');
if (!fs.existsSync(envFile)) {
  fs.writeFileSync(envFile, 
`# Fingerprint System SNS Agent Configuration
# Update these values for your deployment

FP_SERVER_URL=http://your-server:8080
FP_API_KEY=change-me-in-production
`
  );
  console.log(`Created config file: ${envFile}`);
}

console.log('Installation complete!');
console.log('Run "fpsns-agent config" to configure the agent.');
