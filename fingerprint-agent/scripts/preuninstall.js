const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('Uninstalling @fpsns/agent...');

const agentDir = path.join(os.homedir(), '.fpsns-agent');

if (fs.existsSync(agentDir)) {
  console.log(`Removing config directory: ${agentDir}`);
  fs.rmSync(agentDir, { recursive: true, force: true });
}

console.log('Uninstallation complete.');
