# Phase 9 — Match footer/header to demo

**Goal:** bring the live `wear-revamp.myshopify.com` storefront footer in line with the demo (`theme-ritual-demo.myshopify.com`) by wiring the three footer-column menu blocks (SHOP / BRAND / CONNECT) to dedicated Shopify menus, edited directly into the live theme via `themeFilesUpsert`.

## What was wrong

The demo footer renders three grouped accordion columns:

- **SHOP** → Shop all, Bestsellers, New arrivals
- **BRAND** → About us, Blog, Shipping & Returns, Fit guide
- **CONNECT** → Instagram, TikTok, Facebook, Contact us

The wear-revamp Ritual preset (theme `146185617461`, MAIN role) had already created the three menu blocks structurally inside `sections/footer-group.json` — block IDs `menu_ywDwTf`, `menu_UR3gWa`, `menu_4KapTg` — but only the first was wired, and to the wrong menu:

| Block            | Heading | Live `settings.menu` value | Demo expectation        |
| ---------------- | ------- | -------------------------- | ----------------------- |
| `menu_ywDwTf`    | SHOP    | `"footer"` (flat 8-item)   | dedicated `footer-shop` |
| `menu_UR3gWa`    | BRAND   | `""` (empty)               | dedicated `footer-brand`|
| `menu_4KapTg`    | CONNECT | `""` (empty)               | dedicated `footer-connect` |

Result: BRAND and CONNECT columns rendered with their headings but no links; SHOP rendered the wrong link set.

The header (`main-menu`: New / Tops / Bottoms) already matched the demo — no header changes were needed in this phase.

## Fix in 3 sub-steps

### 1. Re-auth with theme scopes added

Previous scope set lacked `read_themes` and `write_themes`, which `theme.files` and `themeFilesUpsert` both require. Re-run with the full set:

```sh
shopify store auth --store wear-revamp.myshopify.com \
  --scopes=read_products,write_products,read_publications,write_publications,write_online_store_navigation,write_content,write_online_store_pages,read_themes,write_themes
```

See [Phase 4](./06-phase-4-auth.md) for the full scope table.

### 2. Create the three dedicated menus

Run `menuCreate` once per column. Each menu has only HTTP-type items (no Shopify-resource references — handles like `/collections/all` resolve at render time).

```graphql
mutation MenuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu { id handle title }
    userErrors { code field message }
  }
}
```

**Variables — `footer-shop`:**

```json
{
  "title": "Footer — Shop",
  "handle": "footer-shop",
  "items": [
    { "title": "Shop all",     "type": "HTTP", "url": "/collections/all" },
    { "title": "Bestsellers",  "type": "HTTP", "url": "/collections/bestsellers" },
    { "title": "New arrivals", "type": "HTTP", "url": "/collections/new" }
  ]
}
```

**Variables — `footer-brand`:**

```json
{
  "title": "Footer — Brand",
  "handle": "footer-brand",
  "items": [
    { "title": "About us",            "type": "HTTP", "url": "/pages/about-us" },
    { "title": "Blog",                "type": "HTTP", "url": "/blogs/news" },
    { "title": "Shipping & Returns",  "type": "HTTP", "url": "/pages/shipping-returns" },
    { "title": "Fit guide",           "type": "HTTP", "url": "/pages/fit-guide" }
  ]
}
```

**Variables — `footer-connect`:**

```json
{
  "title": "Footer — Connect",
  "handle": "footer-connect",
  "items": [
    { "title": "Instagram",  "type": "HTTP", "url": "https://www.instagram.com/" },
    { "title": "TikTok",     "type": "HTTP", "url": "https://www.tiktok.com/" },
    { "title": "Facebook",   "type": "HTTP", "url": "https://www.facebook.com/" },
    { "title": "Contact us", "type": "HTTP", "url": "/pages/contact" }
  ]
}
```

Resulting menu IDs from this run:

- `footer-shop`    → `gid://shopify/Menu/231045169205`
- `footer-brand`   → `gid://shopify/Menu/231045201973`
- `footer-connect` → `gid://shopify/Menu/231045234741`

> ⚠️ The `footer-connect` social URLs are placeholders (root social-platform URLs). Swap them to real handles once those accounts exist.

### 3. Patch `sections/footer-group.json` via `themeFilesUpsert`

Read the live file, do three string replacements on the `menu` settings, write it back.

**Read:**

```graphql
query GetThemeFile($themeId: ID!, $filename: String!) {
  theme(id: $themeId) {
    id
    name
    files(filenames: [$filename]) {
      nodes {
        filename
        body { ... on OnlineStoreThemeFileBodyText { content } }
      }
    }
  }
}
```

**Variables:**

```json
{
  "themeId": "gid://shopify/OnlineStoreTheme/146185617461",
  "filename": "sections/footer-group.json"
}
```

**Write:**

```graphql
mutation ThemeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
  themeFilesUpsert(themeId: $themeId, files: $files) {
    upsertedThemeFiles { filename }
    job { id }
    userErrors { code field message }
  }
}
```

**Variables:**

```json
{
  "themeId": "gid://shopify/OnlineStoreTheme/146185617461",
  "files": [
    {
      "filename": "sections/footer-group.json",
      "body": { "type": "TEXT", "value": "<full file content with the three menu values updated>" }
    }
  ]
}
```

The diff inside the file is exactly three lines:

| Block ID         | Before              | After             |
| ---------------- | ------------------- | ----------------- |
| `menu_ywDwTf`    | `"menu": "footer"`  | `"menu": "footer-shop"`    |
| `menu_UR3gWa`    | `"menu": ""`        | `"menu": "footer-brand"`   |
| `menu_4KapTg`    | `"menu": ""`        | `"menu": "footer-connect"` |

Block `name`s, `heading`s, and styling settings are preserved — only the `menu` reference changes.

> ⚠️ **Order is load-bearing.** Menus must exist (`menuCreate` returns the GID) **before** the theme file is patched to reference them. If you upsert the file first, the columns render empty until the menus are created — and Shopify won't error, it'll just render nothing.

## Why we needed `read_themes` / `write_themes`

| Scope          | What it unlocks                                                              |
| -------------- | ---------------------------------------------------------------------------- |
| `read_themes`  | `theme(id:)` and `theme.files(filenames:)` queries — fetch live theme JSON   |
| `write_themes` | `themeFilesUpsert` mutation — push edited section/template/config files back |

The earlier phases of the cloner only touched data resources (pages, blogs, products, collections, menus), all of which sat under content/navigation scopes. Phase 9 is the first time the cloner edits the **theme code itself**, so two new scopes had to enter the baseline.

## Verify

The storefront has password protection. Authenticate once into a cookie jar, then fetch the homepage past the password gate (password: `revamp`):

```sh
curl -sL -c cookies -b cookies \
  "https://wear-revamp.myshopify.com/password" \
  --data-urlencode "form_type=storefront_password" \
  --data-urlencode "utf8=✓" \
  --data-urlencode "password=revamp" >/dev/null

curl -sL -b cookies "https://wear-revamp.myshopify.com/" \
  | grep -E 'menu__heading__default|footer-(shop|brand|connect)'
```

Expect to see three `<span class="menu__heading__default">` headings (SHOP / BRAND / CONNECT) and the link sets from each menu rendering inside their accordion blocks.

> ⚠️ **Storefront CDN cache lag.** `themeFilesUpsert` returns synchronously, but the rendered storefront sits behind a CDN that can take **30–120 seconds** to refresh. If `curl` still shows the old footer, wait and retry with cache-busting:
>
> ```sh
> curl -sL -b cookies "https://wear-revamp.myshopify.com/?_=$(date +%s%N)" \
>   -H "Cache-Control: no-cache" -H "Pragma: no-cache"
> ```
>
> The admin-side `theme.files` query reflects the upsert immediately, so re-querying that confirms the file was actually written even while the storefront is still serving stale HTML.

## Files changed

- `sections/footer-group.json` — three `settings.menu` values updated:
  - `menu_ywDwTf`: `"footer"` → `"footer-shop"`
  - `menu_UR3gWa`: `""` → `"footer-brand"`
  - `menu_4KapTg`: `""` → `"footer-connect"`

No other theme files, no schema changes, no block additions/removals.

---

After this phase, see [`11-next-steps.md`](./11-next-steps.md) for the remaining two-step continuations (page bodies, collection metadata) and other footer/header polish (real social handles, newsletter signup wiring).
