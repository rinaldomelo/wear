# Phase 2 — Crawl the demo sitemap

**Goal:** discover every product, collection, page, blog, and article handle on
the demo store and persist them as a typed graph at `data/sitemap.json`.

## How it works

```
sitemap.xml                           ← top-level index
├── sitemap_products_1.xml            ← shopify shards by resource type
├── sitemap_collections_1.xml
├── sitemap_pages_1.xml
└── sitemap_blogs_1.xml
       └── article URLs are linked from blog sub-sitemaps
```

`src/crawl/sitemap.ts` walks the index recursively, fetches each shard via the
cache-aware fetcher, and classifies every URL by path:

```ts
function classify(url: string) {
  const parts = new URL(url).pathname.split('/').filter(Boolean);
  if (parts[0] === 'products' && parts[1])           return { kind: 'product',    handle: parts[1] };
  if (parts[0] === 'collections' && parts[1] && !parts[2]) return { kind: 'collection', handle: parts[1] };
  if (parts[0] === 'pages' && parts[1])              return { kind: 'page',       handle: parts[1] };
  if (parts[0] === 'blogs' && parts[1] && !parts[2]) return { kind: 'blog',       handle: parts[1] };
  if (parts[0] === 'blogs' && parts[1] && parts[2])  return { kind: 'article',    handle: `${parts[1]}/${parts[2]}` };
  return { kind: 'other', handle: url };
}
```

## Caching policy

`src/crawl/fetcher.ts` writes every fetched response to
`tools/.cache/<sha1(url)>` and replays it on subsequent runs. This keeps re-runs
polite and **cheap** — only 1 HTTP hit per URL across the entire project.

The fetcher uses Node's native `fetch` with `redirect: 'follow'` (do **not**
swap to `undici@7` — its `request()` no longer accepts `maxRedirections`, which
is what tripped us up the first time around).

## Run it

```sh
cd /Users/melo/clone-shopify/tools
pnpm crawl
```

Output:

```
→ wrote /Users/melo/clone-shopify/tools/data/sitemap.json

Sitemap summary:
  article    6
  blog       1
  collection 12
  page       5
  product    71
```

The numbers above are what we got from theme-ritual-demo. Yours will differ.

## Re-running

The fetcher cache persists, so re-running `pnpm crawl` is a no-op against the
network as long as the demo's sitemap hasn't changed. To force a fresh fetch,
delete `tools/.cache/`.
