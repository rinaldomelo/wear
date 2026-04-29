# Phase 7 — User uploads products

**Goal:** get the product catalog onto the target store. This phase is **out
of scope** for the cloner code — the user does it via Shopify admin's CSV
import or the Matrixify app, not the tool.

## Why we don't automate it (for now)

- Shopify already has a robust CSV product importer in admin and via apps
  like Matrixify. Re-implementing it in `tools/` would just be a worse
  version of those.
- The user already has clean product data. The cloner only needs to know
  *which products belong to which collection* — that lookup happens in
  Phase 8 by handle.

## What the user does

1. Go to *Products → All products → Import* in the target store admin.
2. Upload the CSV (or run Matrixify with images/videos enabled).
3. Wait for the import job to finish — a 71-product catalog with images
   typically takes a few minutes.

## What the cloner expects when Phase 8 runs

- Every product on the target store has a **handle that matches the demo
  store's handle** for the same product. This is the load-bearing
  assumption: handle is how we map demo → target without an explicit
  mapping table.
- Products are **published** to at least one sales channel. (If they aren't,
  they still attach to collections, but won't be visible until Phase 8's
  `publishablePublish` runs against the *collections*. Products themselves
  also need to be published — handle that during the CSV import or run a
  separate `publishablePublish` over products if needed.)

## Verifying

```sh
shopify store execute --store <your-store>.myshopify.com \
  --query 'query { productsCount { count } }'
```

Should return the demo's product count (71 in our run).

To sanity-check handle alignment between demo and target, sample a few:

```sh
# On the demo:
curl -s https://theme-ritual-demo.myshopify.com/products.json?limit=10 \
  | jq '.products[].handle'

# On the target:
shopify store execute --store wear-revamp.myshopify.com \
  --query 'query { products(first: 10) { nodes { handle title } } }'
```

Handles should match. If they don't, Phase 8's "missing" count will be high
and you'll need to either rename products or build an explicit mapping.

## Once products are in place

Continue to [Phase 8 — Sync collections](./10-phase-8-sync-collections.md).
