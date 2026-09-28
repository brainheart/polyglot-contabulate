const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  testMatch: /.*\.spec\.js/,
  timeout: 60000,
  retries: 0,
  workers: 2,
  use: {
    baseURL: 'http://localhost:8791',
    headless: true,
    viewport: { width: 1500, height: 1000 },
  },
  webServer: {
    command: 'python3 -m http.server 8791 -d docs',
    port: 8791,
    stdout: 'ignore',
    stderr: 'ignore',
    reuseExistingServer: false,
  },
});
