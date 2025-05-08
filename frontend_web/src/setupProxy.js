const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  console.log('Setting up proxy middleware...');
  
  const proxy = createProxyMiddleware({
    target: 'http://localhost:5001',
    changeOrigin: true,
    pathRewrite: {
      '^/api': '' // Remove /api prefix when forwarding
    },
    // Add logging for debugging
    logLevel: 'debug',
    onError: (err, req, res) => {
      console.error('Proxy error:', err);
      res.writeHead(500, {
        'Content-Type': 'text/plain'
      });
      res.end(`Proxy error: ${err.message}`);
    },
    onProxyReq: (proxyReq, req, res) => {
      // Log outgoing requests
      console.log(`Proxying ${req.method} request to: ${req.url}`);
      
      // Don't touch headers for multipart/form-data
      if (req.headers['content-type'] && req.headers['content-type'].includes('multipart/form-data')) {
        console.log('Preserving multipart/form-data headers for file upload');
        return;
      }
    },
    onProxyRes: function(proxyRes, req, res) {
      // Log incoming responses
      console.log(`Received ${proxyRes.statusCode} from backend for ${req.url}`);
      
      // Enable CORS
      proxyRes.headers['Access-Control-Allow-Origin'] = '*';
      proxyRes.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization';
      proxyRes.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS';
      
      // Disable caching
      proxyRes.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0';
      proxyRes.headers['Pragma'] = 'no-cache';
      proxyRes.headers['Expires'] = '0';
    }
  });
  
  app.use('/api', proxy);
  
  // Handle OPTIONS requests for CORS preflight
  app.use('/api', (req, res, next) => {
    if (req.method === 'OPTIONS') {
      res.header('Access-Control-Allow-Origin', '*');
      res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
      res.sendStatus(200);
    } else {
      next();
    }
  });
  
  console.log('Proxy middleware setup complete');
}; 