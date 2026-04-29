# Phase 5 — Replicate content (pages, blog, collections, menus)

**Goal:** create on the target store every Admin-API resource the demo has,
*except* products. After this phase the storefront has the right URLs/handles
in place — they're just empty containers waiting for product membership and
real bodies.

## What gets created

| Resource    | Count (this run) | Notes                                       |
| ----------- | ---------------- | ------------------------------------------- |
| Pages       | 4                | about-us, contact, fit-guide, shipping-returns (placeholder bodies) |
| Blog        | 1                | `news` (commentPolicy: MODERATED)           |
| Collections | 8                | new, tops, bottoms, knitwear, dresses, denim, accessories, bestsellers (manual/custom) |
| Menus       | 2                | `main-menu`, `footer` — but see Phase 6 ⚠️  |

## The script

`scripts/replicate-content.sh` — bash wrapper around 16 `shopify store execute`
calls. Every mutation was first validated through the `shopify-admin` skill's
`validate.mjs` so we know the input shapes match the live schema.

Run it after Phase 4 auth:

```sh
cd /Users/melo/clone-shopify/tools
bash scripts/replicate-content.sh
```

## Mutations used

### `pageCreate`

```graphql
mutation CreatePage($page: PageCreateInput!) {
  pageCreate(page: $page) {
    page { id title handle }
    userErrors { code field message }
  }
}
```

Input shape:

```json
{
  "page": {
    "title": "About Us",
    "handle": "about-us",
    "isPublished": true,
    "body": "<p>Placeholder content for about-us.</p>"
  }
}
```

### `blogCreate`

```graphql
mutation CreateBlog($blog: BlogCreateInput!) {
  blogCreate(blog: $blog) {
    blog { id title handle commentPolicy }
    userErrors { code field message }
  }
}
```

Input:

```json
{ "blog": { "title": "News", "handle": "news", "commentPolicy": "MODERATED" } }
```

### `collectionCreate` (manual collection)

```graphql
mutation CollectionCreate($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection { id title handle }
    userErrors { field message }
  }
}
```

Input:

```json
{ "input": { "title": "New", "handle": "new" } }
```

> Omit `ruleSet` to get a manual collection. We populate it with products in
> Phase 8.

### `menuCreate`

```graphql
mutation CreateMenu($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu { id handle items { id title type url } }
    userErrors { code field message }
  }
}
```

Items use `type: HTTP` for URL-based links:

```json
{
  "title": "Main menu",
  "handle": "main-menu",
  "items": [
    { "title": "New",     "type": "HTTP", "url": "/collections/new",     "items": [] },
    { "title": "Tops",    "type": "HTTP", "url": "/collections/tops",    "items": [] },
    { "title": "Bottoms", "type": "HTTP", "url": "/collections/bottoms", "items": [] }
  ]
}
```

> ⚠️ **Handle collision.** Newly initialized stores already have menus with
> handles `main-menu` and `footer`. `menuCreate` succeeds but the result gets a
> suffix (`main-menu-1`, `footer-1`). Phase 6 reconciles this.

## Footer menu items (from extracted nav)

```json
[
  { "title": "Shop all",           "type": "HTTP", "url": "/collections/all" },
  { "title": "Bestsellers",        "type": "HTTP", "url": "/collections/bestsellers" },
  { "title": "New arrivals",       "type": "HTTP", "url": "/collections/new" },
  { "title": "About us",           "type": "HTTP", "url": "/pages/about-us" },
  { "title": "Blog",               "type": "HTTP", "url": "/blogs/news" },
  { "title": "Shipping & Returns", "type": "HTTP", "url": "/pages/shipping-returns" },
  { "title": "Fit guide",          "type": "HTTP", "url": "/pages/fit-guide" },
  { "title": "Contact us",         "type": "HTTP", "url": "/pages/contact" }
]
```

## After this phase

- All target URLs (`/pages/about-us`, `/blogs/news`, `/collections/tops`, …) resolve.
- Page and article bodies are placeholders — real bodies are a [next-steps](./11-next-steps.md) task.
- Collections are empty until [Phase 8](./10-phase-8-sync-collections.md).
- Menus need fixing — see [Phase 6](./08-phase-6-fix-menus.md).
