# Phase 1 — Scaffold the `tools/` workspace

This is a one-time scaffold that lives alongside the Horizon theme files.

## Final layout

```
tools/
├── package.json
├── tsconfig.json
├── pnpm-lock.yaml
├── data/                    # crawl outputs (sitemap.json, nav.json, ...)
├── scripts/
│   ├── replicate-content.sh # creates pages, blog, collections, menus
│   └── fix-menus.sh         # reconciles default main-menu/footer collisions
└── src/
    ├── cli.ts               # commander entry: crawl, extract, sync-collections, all
    ├── config.ts            # DEMO_URL, TARGET_STORE, paths, user agent
    ├── crawl/
    │   ├── fetcher.ts       # rate-limited fetch + on-disk SHA1 cache
    │   ├── sitemap.ts       # walks sitemap.xml + classifies URLs
    │   └── collection-products.ts  # /collections/<h>/products.json paginator
    ├── extract/
    │   ├── nav.ts           # cheerio scrape of <header>/<footer>
    │   └── sections.ts      # Ritual section IDs → Horizon mapping
    └── admin/
        ├── exec.ts          # spawns `shopify store execute`, parses JSON
        └── sync-collections.ts  # collection ↔ product linking + publish
```

## Key config (`src/config.ts`)

```ts
export const DEMO_URL = 'https://theme-ritual-demo.myshopify.com';
export const TARGET_STORE = 'wear-revamp.myshopify.com';
export const TARGET_THEME_ID = '146185617461';
export const USER_AGENT = 'wear-cloner/0.1 (+educational; contact rinaldo@evosem.com)';
export const REQUEST_DELAY_MS = 250;

export const PATHS = {
  cache: '<repo>/tools/.cache',
  data:  '<repo>/tools/data',
  themeRoot: '<repo>',
  templates: '<repo>/templates',
  config:    '<repo>/config',
  sections:  '<repo>/sections',
  assets:    '<repo>/assets',
};
```

When porting to a new site, the only fields you change are `DEMO_URL`,
`TARGET_STORE`, and `TARGET_THEME_ID`.

## `package.json` scripts

```json
{
  "scripts": {
    "crawl":            "tsx src/cli.ts crawl",
    "extract":          "tsx src/cli.ts extract",
    "sync-collections": "tsx src/cli.ts sync-collections",
    "all":              "tsx src/cli.ts all"
  },
  "dependencies": {
    "cheerio": "^1.0.0",
    "commander": "^12.1.0",
    "fast-xml-parser": "^4.5.0",
    "p-limit": "^6.1.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/node": "^22",
    "tsx": "^4.19",
    "typescript": "^5.6"
  }
}
```

## `.gitignore` additions

```
tools/node_modules/
tools/.cache/
tools/dist/
tools/data/*.json
tools/.env
```

> We commit `data/` as a folder (with `.gitkeep`) but ignore the JSON outputs —
> they're regeneratable artifacts of `pnpm crawl` / `pnpm extract`.

## Install

```sh
cd /Users/melo/clone-shopify/tools
pnpm install
```
