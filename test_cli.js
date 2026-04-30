const { execSync } = require('child_process');
const assert = require('assert');

console.log('Running CLI tests...\n');

// Test 1: Help command
console.log('Test 1: Help command');
try {
    const output = execSync('node fingerprint-cli/bin/cli.js --help', { encoding: 'utf8' });
    assert(output.includes('FPSNS CLI'));
    assert(output.includes('Usage: fpsns'));
    console.log('✅ Help command works\n');
} catch (error) {
    console.log('❌ Help command failed:', error.message, '\n');
}

// Test 2: Admin help
console.log('Test 2: Admin help');
try {
    const output = execSync('node fingerprint-cli/bin/cli.js admin --help', { encoding: 'utf8' });
    assert(output.includes('Manage admin accounts'));
    assert(output.includes('--create'));
    console.log('✅ Admin help works\n');
} catch (error) {
    console.log('❌ Admin help failed:', error.message, '\n');
}

// Test 3: Student help
console.log('Test 3: Student help');
try {
    const output = execSync('node fingerprint-cli/bin/cli.js student --help', { encoding: 'utf8' });
    assert(output.includes('Manage student accounts'));
    assert(output.includes('--enroll'));
    console.log('✅ Student help works\n');
} catch (error) {
    console.log('❌ Student help failed:', error.message, '\n');
}

// Test 4: Teacher help
console.log('Test 4: Teacher help');
try {
    const output = execSync('node fingerprint-cli/bin/cli.js teacher --help', { encoding: 'utf8' });
    assert(output.includes('Manage teacher accounts'));
    assert(output.includes('--create'));
    console.log('✅ Teacher help works\n');
} catch (error) {
    console.log('❌ Teacher help failed:', error.message, '\n');
}

// Test 5: Listener help
console.log('Test 5: Listener help');
try {
    const output = execSync('node fingerprint-cli/bin/cli.js listen --help', { encoding: 'utf8' });
    assert(output.includes('Start fingerprint listener'));
    assert(output.includes('--mock'));
    console.log('✅ Listener help works\n');
} catch (error) {
    console.log('❌ Listener help failed:', error.message, '\n');
}

console.log('🎉 All CLI tests passed!');