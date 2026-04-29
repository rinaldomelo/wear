# Phase 11 — Audit and repair collections + products

**Goal:** verify that all 8 target collections on `wear-revamp.myshopify.com` (theme `gid://shopify/OnlineStoreTheme/146185682997`) have the right products, all 71 products are published to every sales channel, and any drift from the original Phase 8 sync is fixed.

## What was wrong

Phase 8 (Sept) ran handle-based: for each target handle it fetched the demo's `/collections/<handle>/products.json` and called `collectionAddProducts`. That left two known issues unverified:

1. **`accessories` was empty.** The demo's collection handle is `accessories-1`, not `accessories`, so Phase 8's request for `/collections/accessories/products.json` 404'd and zero products got linked.
2. **Counts were stale.** The post-Phase-8 numbers (149 links across 7 collections) were never re-verified after subsequent product CSV re-imports and theme work.

User decisions for this phase: keep the 8 target handles, fix the `accessories` mismatch by mapping it to demo's `accessories-1`, leave demo-only collections (`jackets`, `latest-arrivals`, `chair-pointy-shoes`, `rose-back`) out of scope.

## Fix in 2 sub-steps

The flow lives in two scripts:

- [`tools/scripts/audit-collections.py`](../scripts/audit-collections.py) — read-only. Compares live state to the demo and writes `tools/data/collections-audit.json`.
- [`tools/scripts/fix-collections.py`](../scripts/fix-collections.py) — applies fixes from the audit. Idempotent: rerunning after a clean audit is a no-op.

### 1. Audit (read-only)

For each target handle the script:

1. Queries the live `Collection` (id, title, `productsCount`, `resourcePublicationsCount`).
2. Paginates `collection.products(first: 250)` to enumerate currently linked product handles.
3. Fetches the demo's `/collections/<demoHandle>/products.json?limit=250&page=N` for the expected handle set. Demo handle override map: `{ accessories: "accessories-1" }`.
4. Computes:
   - `missing` = demo handles not currently linked AND that exist as a `Product` on wear-revamp (auto-fixable)
   - `unresolved` = demo handles with no matching product on wear-revamp (product upload gap; report only)
   - `extra` = live links not present on the demo (likely manual additions; never auto-removed)

It also walks `products(first: 250)` paginated to compute:
- `productsByStatus` (ACTIVE / DRAFT / ARCHIVED)
- `productsUnpublished` (count < total publications — needs republish)
- `productsOrphaned` (in none of the 8 target collections)

Output snippet from the post-fix run:

```
handle          live  demo  missing  extra  unresolved  pubs
new               30    30        0      0           0     3
tops              17    17        0      0           0     3
bottoms           30    30        0      0           0     3
knitwear           7     7        0      0           0     3
dresses            6     6        0      0           0     3
denim             20    20        0      0           0     3
accessories        4     4        0      0           0     3
bestsellers       39    39        0      0           0     3
```

### 2. Fix

`fix-collections.py` reads `collections-audit.json` and applies three repair categories:

1. **Missing links** → resolve handles to GIDs via `productByHandle`, then `collectionAddProducts(id, productIds)` (chunked at 100).
2. **Under-published collections** → `publishablePublish(id, [{publicationId} ...])` to all sales channels.
3. **Under-published products** → same, per product.

What it deliberately doesn't do:
- Touch `extra` links (the user may have curated them).
- Touch `unresolved` handles (the product doesn't exist on wear-revamp yet — needs CSV upload first).

### Mutations used

```graphql
mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id title productsCount { count } }
    userErrors { field message }
  }
}

mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable { resourcePublicationsCount { count } }
    userErrors { field message }
  }
}
```

> **Note**: `userErrors` on these mutations is the bare `UserError` type (`field` + `message` only). `code` is **not** a field on it — selecting it errors with `Field 'code' doesn't exist on type 'UserError'`. The older `sync-collections.ts` (which selects only `field message`) was already correct; new scripts should match.

## Result

Run summary:

- Audit before fix: `accessories` had 0 live products vs 4 on the demo.
- Fix added 4 products (`rose-11-bag-1`, `rose-11-bag-black`, `rose-11-bag-in-ivory`, `rose-11-bag-red`) to `accessories`.
- Audit after fix: every target collection has `live.count == demo.count`, `missing == 0`, `unresolved == 0`. All 71 products are ACTIVE and published to all 3 sales channels.
- Storefront verified: `https://wear-revamp.myshopify.com/collections/accessories?password=revamp` renders all 4 product cards.

The 2 remaining orphaned products (`silhouette-leather-blazer-black-plain`, `wild-rose-blazer-black-leather`) are intentional — they live only in the demo's `jackets` / `latest-arrivals` collections, which we explicitly chose to skip. Reported, not fixed.

## Why these scripts are Python (not TypeScript)

The cloner's existing TypeScript pipeline (`src/admin/sync-collections.ts`) is the right home for repeatable sync logic. The audit and fix here are one-off / occasional-rerun verification scripts, mirroring the Python pattern from `tools/scripts/sync-footer.sh` and `sync-product.sh` — read-via-CLI, mutate-via-CLI, idempotent. Keeping them in Python lets them run without `pnpm build` and without coupling to the TS module graph.

## Next

After the audit is clean, Phase 12 brings `templates/index.json` (home page) to demo parity: add the missing `layered-slideshow` section, wire the two `collection-list` sections to demo-correct handles, and verify `featured-product` / `product-list` sections reference real products. That's a separate phase — it follows the same read-live → patch → `themeFilesUpsert` pattern as Phases 9 and 10.
