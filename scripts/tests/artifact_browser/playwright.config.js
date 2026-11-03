// Reader acceptance for a built static artifact. GRCInsight has no Node manifest:
// run with an existing @playwright/test 1.62.1 install resolvable by Node, e.g.
//   NODE_PATH=<install>/node_modules node <install>/node_modules/@playwright/test/cli.js \
//     test -c scripts/tests/artifact_browser/playwright.config.js
// Requires STATIC_ARTIFACT_STORE.
const os = require('node:os');
const path = require('node:path');
const { defineConfig } = require('@playwright/test');

const port = process.env.STATIC_ARTIFACT_PORT || '4176';
const store = process.env.STATIC_ARTIFACT_STORE;
const python = process.env.STATIC_ARTIFACT_PYTHON || 'python3';
const repoRoot = path.resolve(__dirname, '..', '..', '..');

if (!store) {
  throw new Error('STATIC_ARTIFACT_STORE must name a store built by scripts/build_static_artifact.py');
}

module.exports = defineConfig({
  testDir: __dirname,
  outputDir: process.env.STATIC_ARTIFACT_PLAYWRIGHT_OUTPUT
    || path.join(os.tmpdir(), 'grcinsight-artifact-playwright'),
  reporter: 'line',
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    browserName: 'chromium',
    colorScheme: 'light',
    locale: 'en-US',
    timezoneId: 'UTC',
  },
  webServer: {
    command: `${python} -B scripts/serve_static_artifact.py --store ${JSON.stringify(store)} --port ${port}`,
    cwd: repoRoot,
    url: `http://127.0.0.1:${port}/`,
    reuseExistingServer: false,
  },
});
