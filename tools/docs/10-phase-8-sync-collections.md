# Phase 8 — Sync collections + publish

**Goal:**

1. For each target collection, fetch the demo's product list, map demo handles
   to target product GIDs, and call `collectionAddProducts`.
2. For every collection on the target store, publish to **all** active sales
   channels via `publishablePublish`.

After this phase the storefront finally shows products under each collection.

## The script

```sh
cd /Users/melo/clone-shopify/tools
pnpm sync-collections     # → tsx src/cli.ts sync-collections
```

Source: `src/admin/sync-collections.ts`. The collection handles to populate
are listed at the top:

```ts
const TARGET_COLLECTION_HANDLES = [
  'new', 'tops', 'bottoms', 'knitwear',
  'dresses', 'denim', 'accessories', 'bestsellers',
];
```

Edit this list when porting to a new site.

## Algorithm

```
1. Fetch publications      (all active sales channels on target)
2. Fetch collections       (target store, by handle → GID)
3. Fetch all products      (target store, paginated 250/page → Map<handle, GID>)

4. For each TARGET_COLLECTION_HANDLE:
     a. Fetch demo's product handles for that collection
        (hits /collections/<handle>/products.json on the demo, paginated)
     b. Resolve handles → target GIDs via the products map
     c. Track 'missing' (handles that exist on demo but not on target)
     d. collectionAddProducts (chunked at 100 IDs per call)
     e. publishablePublish to every sales channel
```

## Why hit `/collections/<h>/products.json` on the demo

The demo store doesn't expose its collection→product membership via Admin API
(we don't have admin access to it). Storefront's public `/products.json`
endpoint per collection is the only reliable, paginated source. The fetcher
caches it like any other URL.

## Mutations used

### `collectionAddProducts`

```graphql
mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id title productsCount { count } }
    userErrors { field message }
  }
}
```

We chunk `productIds` at 100 per call to stay under per-mutation limits.

### `publishablePublish`

```graphql
mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable { resourcePublicationsCount { count } }
    userErrors { field message }
  }
}
```

Input shape:

```json
{
  "id": "gid://shopify/Collection/...",
  "input": [
    { "publicationId": "gid://shopify/Publication/..." },
    { "publicationId": "gid://shopify/Publication/..." },
    { "publicationId": "gid://shopify/Publication/..." }
  ]
}
```

> ⚠️ `Publication.catalog` can be **null** for some publications (e.g., the
> Online Store itself). Use `n.catalog?.title ?? n.id` when logging — don't
> dereference unconditionally. We hit a `Cannot read properties of null` here
> the first time around.

## Output we got

```
→ Fetching publications, collections, products from wear-revamp
  publications=3  collections=9  products=71
    publication: Online Store
    publication: Point of Sale
    publication: Shop

→ Collection: new          demo handles: 30  resolved: 30, missing: 0  → published to 3 channels
→ Collection: tops         demo handles: 17  resolved: 17, missing: 0  → published to 3 channels
→ Collection: bottoms      demo handles: 30  resolved: 30, missing: 0  → published to 3 channels
→ Collection: knitwear     demo handles:  7  resolved:  7, missing: 0  → published to 3 channels
→ Collection: dresses      demo handles:  6  resolved:  6, missing: 0  → published to 3 channels
→ Collection: denim        demo handles: 20  resolved: 20, missing: 0  → published to 3 channels
→ Collection: accessories  demo handles:  0  resolved:  0, missing: 0  → published to 3 channels
→ Collection: bestsellers  demo handles: 39  resolved: 39, missing: 0  → published to 3 channels

✓ Collection sync complete.
```

149 collection↔product links across 7 non-empty collections, 100% handle
match rate.

## Idempotency

`collectionAddProducts` is additive — running twice doesn't duplicate
membership, but it also doesn't *remove* products that no longer match the
demo. If you need a strict mirror, add a `collectionRemoveProducts` step that
diffs current target membership against demo handles.
