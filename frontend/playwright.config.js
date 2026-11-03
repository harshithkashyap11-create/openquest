import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  workers: 1,
  timeout: 45000,
  expect: { timeout: 12000 },
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5181',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command: 'python3 ../scripts/run_quiz_test_api.py',
      url: 'http://127.0.0.1:8012/health',
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command:
        process.env.CLASSPULSE_TEST_PRODUCTION === '1'
          ? 'npm run preview -- --host 127.0.0.1 --port 5181 --strictPort'
          : 'npm run dev -- --host 127.0.0.1 --port 5181 --strictPort',
      url: 'http://127.0.0.1:5181',
      env: {
        CLASS_PULSE_BACKEND_URL: 'http://127.0.0.1:8012',
        VITE_API_BASE_URL: '/api',
      },
      reuseExistingServer: false,
    },
  ],
});
