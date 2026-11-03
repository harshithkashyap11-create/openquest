import { readdir, readFile } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { gzipSync, brotliCompressSync } from 'node:zlib';
const root = process.argv[2] ?? 'frontend/dist';
async function walk(dir) {
  const files = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...(await walk(path)));
    else files.push(path);
  }
  return files;
}
const results = [];
for (const file of await walk(root)) {
  if (!/\.(js|css|woff2?)$/.test(file)) continue;
  const data = await readFile(file);
  results.push({
    file: relative(root, file),
    rawBytes: data.length,
    gzipBytes: gzipSync(data, { level: 9 }).length,
    brotliBytes: brotliCompressSync(data).length,
  });
}
results.sort((a, b) => b.gzipBytes - a.gzipBytes);
if (process.argv.includes('--json'))
  console.log(JSON.stringify(results, null, 2));
else {
  console.table(results);
  console.log(
    'Asset totals are not entry-route transfer. Use the browser resource set in profile-frontend.mjs for route gzip comparisons.',
  );
}
