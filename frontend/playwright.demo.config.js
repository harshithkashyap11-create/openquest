import base from './playwright.config.js';
import { defineConfig } from '@playwright/test';

export default defineConfig({
  ...base,
  testDir: './demo-tests',
  timeout: 120000,
  webServer: base.webServer.map((server, index) => index === 0 ? {
    ...server,
    env: { OPENPOST_MAP_DEMO: '1' },
  } : server),
});
