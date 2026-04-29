# Phase 3 — Extract nav + homepage sections

**Goal:** scrape the demo's header/footer link lists and the homepage section
order, write them to `data/nav.json` and `data/homepage-sections.json`.

These outputs are *informational* — they tell us which menu links and section
choices the target store should mirror. We use them when authoring
`scripts/replicate-content.sh` (menu items) and when reviewing whether the
preset's homepage already matches the demo.

## Nav extraction (`src/extract/nav.ts`)

Loads the demo homepage HTML, then uses cheerio to pull every `<a>` inside
`<header>` and `<footer>` landmarks:

```ts
const $ = cheerio.load(html);
const header = $('header a').map(...).get();
const footer = $('footer a').map(...).get();
```

Each link is normalized to `{ title, url }` with relative URLs resolved against
the demo origin. Output:

```json
{
  "header": [{ "title": "New",  "url": "/collections/new" }, ...],
  "footer": [{ "title": "Shop all", "url": "/collections/all" }, ...]
}
```

## Section extraction (`src/extract/sections.ts`)

The homepage HTML embeds Ritual section IDs in `data-section-type` attributes.
We read them in DOM order and map to the closest Horizon section name:

```ts
const RITUAL_TO_HORIZON: Record<string, string> = {
  'featured-product':   'featured-product',
  'product-list':       'product-list',
  'collection-list':    'collection-list',
  'layered-slideshow':  'layered-slideshow',
  marquee:              'marquee',
  // Unknown ritual types fall through and are recorded as `horizonType: null`
};
```

Output `data/homepage-sections.json`:

```json
[
  { "order": 1, "ritualType": "header",            "horizonType": null },
  { "order": 2, "ritualType": "category-grid",     "horizonType": null },
  { "order": 3, "ritualType": "featured-product",  "horizonType": "featured-product" },
  ...
]
```

## Run it

```sh
cd /Users/melo/clone-shopify/tools
pnpm extract
```

Output ends with a printed table you can eyeball:

```
Header: 4 links, Footer: 8 links
Homepage sections: 9
Section order:
   1. header              → UNMAPPED
   2. category-grid       → UNMAPPED
   3. featured-product    → featured-product
   ...
```

## What we DO with this output

- The footer link list informs the items we hardcode in `scripts/replicate-content.sh` for the `footer` menu (urls + titles).
- The header link list informs the `main-menu` items.
- The section order is currently informational — we don't push templates. If a
  future scope expands to "also write the theme's `templates/index.json`", this
  is the input you'd feed it.
