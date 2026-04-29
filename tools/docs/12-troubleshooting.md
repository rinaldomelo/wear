# 12 — Troubleshooting (errors we hit and how to fix them)

## `InvalidArgumentError: maxRedirections is not supported, use the redirect interceptor`

**Where:** `src/crawl/fetcher.ts` while crawling the demo.

**Why:** undici v7 removed the `maxRedirections` option from `request()`. The
project initially used `undici.request(url, { maxRedirections: 5 })`.

**Fix:** drop undici, use Node's native `fetch` with `redirect: 'follow'`:

```ts
const res = await fetch(url, {
  headers: { 'user-agent': USER_AGENT, accept: '*/*' },
  redirect: 'follow',
});
```

Node 18+ has native fetch; we're on Node 25.

---

## `Flag --scopes expects a value`

**Where:** running `shopify store auth ...`.

**Why:** the shell wrapped the command across newlines without a trailing
backslash, so the second line was parsed as a separate command and `--scopes`
ended up flagless.

**Fix:** put the whole command on one line, use `--scopes=...` (with `=`):

```sh
shopify store auth --store wear-revamp.myshopify.com \
  --scopes=read_products,write_products,read_publications,write_publications,write_online_store_navigation,write_content,write_online_store_pages
```

(That `\` is a real continuation; if your terminal eats it, just keep it all on one line.)

---

## `Access denied for publications. Required access: read_publications`

**Where:** Phase 8 publications query.

**Why:** initial scope set didn't include publications scopes.

**Fix:** re-run `shopify store auth` with the extended scope set listed in
[Phase 4](./06-phase-4-auth.md). Tokens are replaced; no need to revoke first.

---

## `Cannot read properties of null (reading 'title')` on Publication

**Where:** `src/admin/sync-collections.ts` when logging publications.

**Why:** `Publication.catalog` is nullable. Some publications (e.g., Online
Store) return `catalog: null`.

**Fix:**

```ts
interface PublicationsResp {
  publications: { nodes: Array<{ id: string; catalog: { title: string } | null }> };
}
// ...
return resp.publications.nodes.map((n) => ({
  id: n.id,
  title: n.catalog?.title ?? n.id,
}));
```

---

## Menu handles became `main-menu-1` / `footer-1`

**Where:** Phase 5 `menuCreate`.

**Why:** Shopify reserves the default `main-menu` and `footer` handles, so a
new menu with those handles gets a numeric suffix appended.

**Fix:** see [Phase 6](./08-phase-6-fix-menus.md) — `menuUpdate` the originals,
then `menuDelete` the suffixed duplicates.

---

## `shopify store execute: unknown command`

**Where:** any phase that uses the CLI.

**Why:** Shopify CLI < 3.93.0 doesn't have `store execute`.

**Fix:** upgrade:

```sh
brew upgrade shopify-cli   # or: npm i -g @shopify/cli@latest
shopify version            # confirm ≥ 3.93.0
```

---

## `No JSON in shopify output`

**Where:** `src/admin/exec.ts`.

**Why:** `shopify store execute` printed informational lines to stdout and
the response wasn't valid JSON to begin with — usually an auth/CLI error
masquerading as a successful exit.

**Fix:**

1. Add `--json` to the args (we already do; double-check it's passed).
2. Run the failing command manually with the same args printed by the spawn
   to see the real stderr output.
3. If the stderr is "needs auth", re-run Phase 4.

---

## `productCreate userErrors: handle is already taken`

**Where:** if/when product creation is added (currently Phase 7 is manual).

**Why:** trying to create a product whose handle already exists.

**Fix:** make the importer idempotent — query `productByHandle` first; if
present, run `productUpdate` instead. Or rely on Shopify CSV import which
handles upserts natively.

---

## Storefront still shows old footer/header after `themeFilesUpsert`

**Where:** Phase 9 — after pushing a `sections/*.json` change.

**Why:** Shopify storefront has a CDN cache layer. The theme file in admin is updated immediately, but the rendered storefront can lag by 30–120 seconds.

**Fix:** wait, then re-fetch with cache-busting query string + headers:

```sh
curl -sL -b cookies "https://<store>.myshopify.com/?_=$(date +%s%N)" \
  -H "Cache-Control: no-cache" -H "Pragma: no-cache"
```

You can also re-query the live theme file with the `theme.files` query to confirm admin-side correctness — that should reflect the upsert immediately.

---

## Footer column block renders empty after wiring a menu handle

**Where:** Phase 9 — after editing `sections/footer-group.json` to point a menu block at a new handle.

**Why:** the menu handle in the block's `settings.menu` field must already exist as a Shopify menu when the storefront renders. If you edit the theme file before running `menuCreate`, the column renders empty until the menu exists.

**Fix:** always create the menus FIRST (`menuCreate`), then patch the theme file second. Order is load-bearing.
