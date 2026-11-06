import config from './playwright.config.js';
export default { ...config, use: { ...config.use, baseURL: 'http://127.0.0.1:5198' }, webServer: [config.webServer[0], { ...config.webServer[1], command: 'npm run dev -- --host 127.0.0.1 --port 5198 --strictPort', url: 'http://127.0.0.1:5198' }] };
