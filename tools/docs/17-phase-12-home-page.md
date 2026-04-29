# Phase 12 — Match the home page to the demo

**Goal:** bring `templates/index.json` on `wear-revamp.myshopify.com` (theme `gid://shopify/OnlineStoreTheme/146185682997`) to parity with the Ritual demo's home page (`https://theme-ritual-demo.myshopify.com/`).

## What was wrong

Same root cause as Phases 9 and 10: the Ritual preset wrote a different shape than the demo. Differences between the live home and the demo:

| | Demo | Live (Ritual preset) |
| - | - | - |
| **Section count** | 6 (logo, collection-list grid, featured-product, product-list, layered-slideshow, marquee) | 6 (logo, collection-list **grid**, featured-product, product-list, **second** collection-list **carousel**, marquee) |
| **collection-list (grid)** | 4 cards: knitwear, dresses, denim, bottoms | empty `collection_list` setting → renders placeholder cards |
| **featured-product** | `rose-11-bag-1` | empty `product` setting → renders placeholder |
| **product-list** | collection: `all`, 4 cards | same shape — kept as-is |
| **2nd section** | `layered-slideshow` with 3 slides + bg images | `collection-list` carousel (no images, no handles) |
| **marquee** | "SHOP NOW" → `/collections/all` | same — kept as-is |

The two structural moves: drop the second collection-list and add a layered-slideshow with 3 slides. Plus wiring the existing collection-list grid + featured-product to real handles.

## Fix in one script

The flow lives in [`tools/scripts/sync-home.py`](../scripts/sync-home.py). It is idempotent — it skips upload and re-patches in place when the live file is already in target shape (it still pulls the file back into the repo).

### 1. Upload the 3 demo slideshow images into wear-revamp's Files

The demo's CDN serves the originals; we ingest them into wear-revamp's own Files via `fileCreate(originalSource: <demoCdnUrl>)`. The script first scans `files(first: 100, ...)` for already-uploaded images matching our 3 alt strings — if all 3 are READY, it reuses their GIDs instead of re-uploading.

```graphql
mutation fileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id alt fileStatus ... on MediaImage { image { url } } }
    userErrors { field message }
  }
}
```

After upload, poll `node(id: ...) { ... on MediaImage { fileStatus image { url } } }` until `fileStatus == "READY"`. That `image.url` is the wear-revamp CDN URL — extract its filename to build the image-picker reference (see step 3).

### 2. Read live `templates/index.json`

Same `theme.files(filenames: [$filename])` query as Phases 9/10. The file body has a `/* auto-generated */` comment header — preserve it verbatim and parse only what follows.

### 3. Build the patched JSON in memory

Five edits to the live data:

1. `sections.collection_list_FFV7jq.settings.collection_list = ["knitwear", "dresses", "denim", "bottoms"]`
2. `sections.featured_product_pW7dEU.settings.product = "rose-11-bag-1"`
3. Delete `sections.collection_list_iAQiBH` (the Ritual preset's extra carousel)
4. Insert `sections.layered_slideshow_A6t8QQ` — `type: "layered-slideshow"` with 3 `_layered-slide` blocks. Each slide has heading + body + button child blocks plus slide-level settings:
   ```jsonc
   "settings": {
     "media_type_1": "image",
     "image_1": "shopify://shop_images/<filename>"
   }
   ```
5. Replace `order` with `["section_Fh7TFQ", "collection_list_FFV7jq", "featured_product_pW7dEU", "product_list_8kR3Hb", "layered_slideshow_A6t8QQ", "marquee_9AMajF"]`

### 4. Upsert + pull back

`themeFilesUpsert` with the new content, then re-read the live file and write to the repo's `templates/index.json` so git matches live.

```graphql
mutation ThemeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    userErrors { code field message }
  }
}
```

## Gotcha: image_picker setting expects a `shopify://` URL, not a GID

First attempt set `image_1` to the freshly uploaded `gid://shopify/MediaImage/29998941208629`. `themeFilesUpsert` rejected it:

```
FILE_VALIDATION_ERROR: Setting 'image_1' must be a valid shopify url
```

The `image_picker` setting type stores values as `shopify://shop_images/<filename>` — the filename being whatever Shopify renamed the asset to (in our case Shopify converted `79.webp?v=...` → `79.jpg`). Get the filename out of the post-upload `image.url` (after the last `/`, before the `?v=...`).

## Slide content (verbatim from the demo)

Three slides, each with heading + body + CTA. Demo's CTA links and labels were a little inconsistent (e.g. button labelled "SHOP BESTSELLERS" pointing at `/collections/all`); for wear-revamp we tightened them so each label points to the matching collection:

| Slide | Heading | Body (paraphrased from demo) | Label | Link |
| - | - | - | - | - |
| 1 | Rise to the top | Architectural blazers, sleek camis and effortlessly distressed tees fit every mood and occasion. | SHOP TOPS | `shopify://collections/tops` |
| 2 | Iconic for a reason | Our bestselling pieces are equal parts refined and provocative. | SHOP BESTSELLERS | `shopify://collections/bestsellers` |
| 3 | Fashion forward | Uncover our newest, highly experimental designs. | SHOP NEW ARRIVALS | `shopify://collections/new` |

## Verification

After upsert:

1. Re-read `templates/index.json` via `theme.files`; confirm the new `order`, the slideshow section, the wired collection_list, the featured-product handle.
2. Curl the storefront with the password cookie (cache-buster `?_=$(date +%s%N)` if needed):
   ```
   curl -sL -b cookies "https://wear-revamp.myshopify.com/?_=..." \
     -H "Cache-Control: no-cache"
   ```
   Expected sections (in this order): `section_Fh7TFQ`, `collection_list_FFV7jq`, `featured_product_pW7dEU`, `product_list_8kR3Hb`, `layered_slideshow_A6t8QQ`, `marquee_9AMajF`.
3. Confirm 3 slideshow images render from `wear-revamp.myshopify.com/cdn/shop/files/{79,Untitled_design,251108_SEENUSERS_CK_15_094_F2C}.jpg`.
4. Confirm featured-product link is `/products/rose-11-bag-1`.
5. Confirm grid carries all 4 collection links: `/collections/{knitwear,dresses,denim,bottoms}`.

## Idempotency

Re-running `sync-home.py` after a successful run:
- Detects `layered-slideshow` already present + carousel absent + handles already wired → short-circuits to "already in target shape".
- Otherwise proceeds, but reuses the 3 alt-matched MediaImage GIDs instead of re-uploading.

So a retry after a partial failure is safe — no duplicate Files records, no double-edit.
