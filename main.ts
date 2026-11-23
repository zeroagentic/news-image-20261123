// Entry point for the make.fun bounty news-image-20261123.
// Copies the front page drawn by gen.py (entry.png, beside this module) into
// $MAKEFUN_OUTPUT_DIR/entry.png, or /output/entry.png when that is unset.
// The picture is copied byte for byte, so two runs write identical files.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const LIMIT = 1048576;                                  // 1 MiB, the gate's cap
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

const source = fileURLToPath(new URL('./entry.png', import.meta.url));
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const target = join(outDir, 'entry.png');

let bytes;
try {
  bytes = readFileSync(source);
} catch (err) {
  const why = err?.code === 'ENOENT' ? 'no such file' : 'unreadable';
  throw new Error(`cannot read the picture at ${source}: ${why}`);
}
if (bytes.length === 0) {
  throw new Error(`picture is empty at ${source}`);
}
if (bytes.length > LIMIT) {
  throw new Error(`picture is ${bytes.length} bytes, over the ${LIMIT}-byte limit: ${source}`);
}
if (!bytes.subarray(0, 8).equals(PNG)) {
  throw new Error(`not a PNG (bad signature) at ${source}`);
}

mkdirSync(dirname(target), { recursive: true });
writeFileSync(target, bytes);
console.log(`wrote ${target} (${bytes.length} bytes)`);
