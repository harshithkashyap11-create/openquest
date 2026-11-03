import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import zlib from 'node:zlib';
const [url, out, dist] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 360, height: 780 },
});
const page = await context.newPage();
await page.addInitScript(() => {
  window.lab = { cls: 0, lcp: 0, longTasks: [], events: [] };
  new PerformanceObserver((l) =>
    l.getEntries().forEach((e) => {
      if (!e.hadRecentInput) window.lab.cls += e.value;
    }),
  ).observe({ type: 'layout-shift', buffered: true });
  new PerformanceObserver((l) =>
    l.getEntries().forEach((e) => (window.lab.lcp = e.startTime)),
  ).observe({ type: 'largest-contentful-paint', buffered: true });
  new PerformanceObserver((l) =>
    l.getEntries().forEach((e) => window.lab.longTasks.push(e.duration)),
  ).observe({ type: 'longtask', buffered: true });
});
const cdp = await context.newCDPSession(page);
await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
await cdp.send('Network.enable');
await cdp.send('Network.emulateNetworkConditions', {
  offline: false,
  latency: 400,
  downloadThroughput: 50000,
  uploadThroughput: 50000,
  connectionType: 'cellular3g',
});
await page.goto(url + '/login');
await page.waitForLoadState('networkidle');
await page.getByRole('combobox').last().waitFor();
const lab = await page.evaluate(() => ({
  ...window.lab,
  resources: performance
    .getEntriesByType('resource')
    .map((e) => ({
      url: e.name,
      transfer: e.transferSize,
      decoded: e.decodedBodySize,
    })),
}));
lab.profile =
  'Chromium headless, 360×780,4xCPU,400ms latency,50KB/s each direction (Slow3G simulation)';
lab.js = lab.resources
  .filter((r) => /\.js($|\?)/.test(r.url))
  .map((r) => {
    const file = new URL(r.url).pathname;
    const buf = fs.readFileSync(dist + file);
    return {
      ...r,
      gzip: zlib.gzipSync(buf, { level: 9 }).length,
      brotli: zlib.brotliCompressSync(buf).length,
    };
  });
lab.entryGzip = lab.js.reduce((n, r) => n + r.gzip, 0);
lab.entryTransferred = lab.js.reduce((n, r) => n + r.transfer, 0);
fs.writeFileSync(out, JSON.stringify(lab, null, 2));
console.log(
  JSON.stringify({
    cls: lab.cls,
    lcp: lab.lcp,
    entryGzip: lab.entryGzip,
    entryTransferred: lab.entryTransferred,
    longTasks: lab.longTasks,
  }),
);
await browser.close();
