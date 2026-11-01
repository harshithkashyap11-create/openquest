import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../frontend/src/i18n');
const languages = ['en', 'hi', 'te'];
const dictionaries = Object.fromEntries(
  await Promise.all(
    languages.map(async (language) => [
      language,
      JSON.parse(await readFile(resolve(root, `${language}.json`), 'utf8')),
    ]),
  ),
);
const expected = new Set(Object.keys(dictionaries.en));
let missingCount = 0;

for (const language of languages.slice(1)) {
  const missing = [...expected].filter((key) => !(key in dictionaries[language]));
  const extra = Object.keys(dictionaries[language]).filter((key) => !expected.has(key));
  if (missing.length || extra.length) {
    missingCount += missing.length + extra.length;
    console.warn(`${language}: missing [${missing.join(', ')}], extra [${extra.join(', ')}]`);
  } else {
    console.log(`${language}: key set matches en (${expected.size} keys)`);
  }
}

if (missingCount) console.warn(`Found ${missingCount} translation key mismatch(es).`);
