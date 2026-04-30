const fs = require('fs');
const path = require('path');

const binPath = path.join(__dirname, '..', 'bin', 'fpsns.js');

// Set executable flag on Unix systems (no-op on Windows)
try {
  if (process.platform !== 'win32') {
    fs.chmodSync(binPath, '755');
  }
} catch (e) {
  console.warn('Could not set executable flag:', e.message);
}

console.log('✓ fpsns installed successfully');
