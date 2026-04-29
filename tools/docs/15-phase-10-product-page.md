# Phase 10 — Match the product page to the demo

**Goal:** bring the live `wear-revamp.myshopify.com` product detail page (PDP) in line with the Ritual demo (`theme-ritual-demo.myshopify.com/products/<handle>`) by editing `templates/product.json` directly on the live theme via `themeFilesUpsert`. Same pattern as Phase 9.

## What was wrong

Three differences between the live PDP and the demo:

| | Demo (Ritual) | Live (Horizon + Ritual preset) |
| - | - | - |
| **Buy buttons** | Single "Add to cart" | Add to cart + accelerated-checkout (Shop Pay / Buy Now) |
| **Below-fold row** | Static row of 6 collection cards under "Goes well with..." | Dynamic `product-recommendations` (algorithmic) AND an empty `collection-links` section the preset stamped in |
| **Shipping/returns notice** | Small notice next to buy button (Ritual deferred-purchase copy) | Not present |

Header on the PDP already matched the demo from Phase 9 — no header changes here.

User decisions for this phase:
- Drop `accelerated-checkout` to match the demo's interface (checkout isn't enabled on wear-revamp anyway).
- Replace `product-recommendations` with a static `collection-list` section showing the same 6 collections the demo highlights.
- Add a Wear-branded shipping/returns notice (drop the Ritual-specific copy).

## Fix in 3 sub-steps

The whole flow lives in [`tools/scripts/sync-product.sh`](../scripts/sync-product.sh). It is idempotent — re-running it produces no diff.

### 1. Read live `templates/product.json`

The live file differs from the repo (Ritual preset wrote different block IDs and a different block_order). Always patch from the live file.

```graphql
query GetThemeFile($themeId: ID!, $filename: String!) {
  theme(id: $themeId) {
    files(filenames: [$filename]) {
      nodes {
        filename
        body { ... on OnlineStoreThemeFileBodyText { content } }
      }
    }
  }
}
```

```json
{
  "themeId": "gid://shopify/OnlineStoreTheme/146185617461",
  "filename": "templates/product.json"
}
```

### 2. Patch the JSON in memory

Three structural edits, plus one new block:

| Path | Change |
| - | - |
| `sections.main.blocks.product-details.blocks.buy_buttons.blocks.accelerated-checkout` | **deleted** |
| `sections.main.blocks.product-details.blocks` | **add** `text_wear_notice` text block ("Free shipping over $75 · 30-day returns") |
| `sections.main.blocks.product-details.block_order` | insert `text_wear_notice` after the description text |
| `sections.product-recommendations` (or any `product_recommendations_*`) | **deleted** |
| `sections.<*>` of type `collection-links` | **deleted** (the empty preset leftover) |
| `sections.collection_list_goes_well` | **added** — `collection-list` section with `collection_list: [bestsellers, dresses, tops, accessories, bottoms, denim]` and a `<h3>Goes well with...</h3>` header text block |
| `order` | replaced with `["main", "collection_list_goes_well"]` |

The new `collection_list_goes_well` section's `static-collection-card` static block has nested static `_collection-card-image` and a non-static `collection-title`. Two validator gotchas surfaced here:

- The schema requires `collection-title` to be **present** in `block_order` of `static-collection-card`.
- It also requires the static `_collection-card-image` to be **absent** from that same `block_order`.

Final `block_order` on the static card: `["collection-title"]`.

### 3. Upsert via `themeFilesUpsert`

```graphql
mutation ThemeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    job { id }
    userErrors { code field message }
  }
}
```

The full file (with the `/* auto-generated */` header preserved) goes in as `body.value`.

## Why no new scopes

`read_themes` and `write_themes` already entered the baseline in Phase 9. No scope change this phase.

## Verify

Admin-side (immediate) — re-run the `theme.files` query and check shape:

```sh
shopify store execute --store wear-revamp.myshopify.com \
  --query 'query GetThemeFile($themeId: ID!, $filename: String!) { theme(id: $themeId) { files(filenames: [$filename]) { nodes { filename body { ... on OnlineStoreThemeFileBodyText { content } } } } } }' \
  --variables '{"themeId":"gid://shopify/OnlineStoreTheme/146185617461","filename":"templates/product.json"}' \
  | python3 -c "import json,re,sys; d=json.load(sys.stdin); inner=d.get('data',d); raw=inner['theme']['files']['nodes'][0]['body']['content']; data=json.loads(re.sub(r'^/\\*.*?\\*/\\s*','',raw,flags=re.S)); print(data['order']); print('accel:', 'accelerated-checkout' in data['sections']['main']['blocks']['product-details']['blocks']['buy_buttons']['blocks']); print('cl:', data['sections'].get('collection_list_goes_well',{}).get('settings',{}).get('collection_list'))"
```

Expected:

```
['main', 'collection_list_goes_well']
accel: False
cl: ['bestsellers', 'dresses', 'tops', 'accessories', 'bottoms', 'denim']
```

Storefront (allow 30–120 s for CDN cache; same lag as Phase 9). With the password cookie (`revamp`), curl a real product:

```sh
curl -sL -c cookies -d "form_type=storefront_password&utf8=%E2%9C%93&password=revamp" \
  "https://wear-revamp.myshopify.com/password" >/dev/null
curl -sL -b cookies -H "Cache-Control: no-cache" \
  "https://wear-revamp.myshopify.com/products/<any-handle>?_=$(date +%s%N)" \
  | grep -E 'Goes well with|You may also like|Free shipping over|/collections/(bestsellers|dresses|tops|accessories|bottoms|denim)'
```

Expect: "Goes well with..." heading present, no "You may also like", "Free shipping over $75 · 30-day returns" rendered, all six collection hrefs present.

> ⚠️ **`shopify-accelerated-checkout` in JS isn't the block.** Shopify includes a global wallet-skeleton script on every storefront. A grep for that string still matches even when the buy-buttons block omits the `accelerated-checkout` child. Validate the block's absence by re-querying the JSON template, not by greping the rendered HTML.

## Files changed

- **Live theme `templates/product.json`** — full restructure (see step 2). Not committed to git; the GitHub-connected repo only carries the pre-Ritual-preset version.
- **`tools/scripts/sync-product.sh`** — new idempotent sync script for this phase.

No other theme files touched.

## Idempotency

`sync-product.sh` runs the same patches every time. The Python step compares the new serialized body against the original; on a no-op run, the upsert receives the same content and lands as a no-op. Block IDs are stable (`text_wear_notice`, `collection_list_goes_well`) so re-runs don't drift.

---

After this phase, see [`11-next-steps.md`](./11-next-steps.md) for the remaining two-step continuations (page bodies, collection metadata) and any further demo-parity polish.
