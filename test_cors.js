const http = require('http');

// Test CORS preflight
const options = {
  hostname: 'localhost',
  port: 8000,
  path: '/api/v1/auth/register',
  method: 'OPTIONS',
  headers: {
    'Origin': 'http://localhost:8081',
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'Content-Type'
  }
};

const req = http.request(options, (res) => {
  console.log(`Status: ${res.statusCode}`);
  console.log(`Headers:`, res.headers);
  
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    console.log('Response:', data);
  });
});

req.on('error', (e) => {
  console.error(`Problem with request: ${e.message}`);
});

req.end();