import test from 'node:test';
import assert from 'node:assert/strict';
import QRCode from 'qrcode';
import jsQR from 'jsqr';
import { PNG } from 'pngjs';
import { scannedCard } from '../src/services/qrCards.js';

test('real response cards decode the four printed answer orientations', async () => {
  const png = PNG.sync.read(await QRCode.toBuffer(JSON.stringify({ app: 'classpulse', class_id: 'class-1', student_id: 'student-1' }), { width: 300 }));
  let pixels = png.data;
  for (const expected of [0, 3, 2, 1]) {
    const code = jsQR(new Uint8ClampedArray(pixels), png.width, png.height);
    assert.ok(code);
    assert.deepEqual(scannedCard(code, 'class-1'), { student_id: 'student-1', option: expected });
    assert.equal(scannedCard(code, 'another-class'), null);
    const rotated = new Uint8Array(pixels.length);
    for (let y = 0; y < png.height; y++) for (let x = 0; x < png.width; x++) {
      const from = (y * png.width + x) * 4, to = (x * png.width + png.width - 1 - y) * 4;
      rotated.set(pixels.slice(from, from + 4), to);
    }
    pixels = rotated;
  }
});
