import { resolve } from 'node:path';

export const DEMO_URL = 'https://theme-ritual-demo.myshopify.com';
export const TARGET_STORE = 'wear-revamp.myshopify.com';
export const TARGET_THEME_ID = '146185617461';

const ROOT = resolve(import.meta.dirname, '..');

export const PATHS = {
  cache: resolve(ROOT, '.cache'),
  data: resolve(ROOT, 'data'),
  themeRoot: resolve(ROOT, '..'),
  templates: resolve(ROOT, '..', 'templates'),
  config: resolve(ROOT, '..', 'config'),
  sections: resolve(ROOT, '..', 'sections'),
  assets: resolve(ROOT, '..', 'assets'),
} as const;

export const USER_AGENT =
  'wear-cloner/0.1 (+educational; contact rinaldo@evosem.com)';

export const REQUEST_DELAY_MS = 250;
