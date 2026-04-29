import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import pLimit from 'p-limit';
import { PATHS, REQUEST_DELAY_MS, USER_AGENT } from '../config.js';

const limit = pLimit(4);
let lastRequest = 0;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function cacheKey(url: string) {
  return createHash('sha1').update(url).digest('hex');
}

export async function fetchCached(url: string): Promise<string> {
  const key = cacheKey(url);
  const file = join(PATHS.cache, `${key}.txt`);
  try {
    return await readFile(file, 'utf8');
  } catch {}

  return limit(async () => {
    const wait = REQUEST_DELAY_MS - (Date.now() - lastRequest);
    if (wait > 0) await sleep(wait);
    lastRequest = Date.now();

    const res = await fetch(url, {
      headers: { 'user-agent': USER_AGENT, accept: '*/*' },
      redirect: 'follow',
    });
    if (!res.ok) {
      throw new Error(`Fetch ${url} → HTTP ${res.status}`);
    }
    const body = await res.text();
    await mkdir(PATHS.cache, { recursive: true });
    await writeFile(file, body, 'utf8');
    return body;
  });
}
