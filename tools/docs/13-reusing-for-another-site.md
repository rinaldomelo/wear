# 13 — Reusing this for another demo / target site

A diff-style checklist for when you point this cloner at a new pair of stores.

## What changes per run

| Thing                          | Where to change it                              |
| ------------------------------ | ----------------------------------------------- |
| Demo URL                       | `src/config.ts` → `DEMO_URL`                    |
| Target store domain            | `src/config.ts` → `TARGET_STORE`                |
| Target theme ID                | `src/config.ts` → `TARGET_THEME_ID`             |
| Collection handles to populate | `src/admin/sync-collections.ts` → `TARGET_COLLECTION_HANDLES` |
| Pages to create                | `scripts/replicate-content.sh` (page block at top) |
| Blog handle / title            | `scripts/replicate-content.sh`                  |
| Collection list to *create*    | `scripts/replicate-content.sh`                  |
| Menu items                     | `scripts/replicate-content.sh` + `scripts/fix-menus.sh` |
| Default menu IDs (for fix)     | `scripts/fix-menus.sh` — look up live, see Phase 6 |
| User agent / contact email     | `src/config.ts` → `USER_AGENT`                  |
| Theme scopes (`read_themes` / `write_themes`) | [`06-phase-4-auth.md`](./06-phase-4-auth.md) |
| Footer menu handles (`footer-shop` / `footer-brand` / `footer-connect`) | [`14-phase-9-match-footer-header.md`](./14-phase-9-match-footer-header.md) |
| Footer block IDs in `sections/footer-group.json` | live theme — must be looked up per store via `theme.files` query |
| PDP "Goes well with" collection handles (6 entries in `collection_list`) | `tools/scripts/sync-product.sh` — the array passed into `collection_list` on `collection_list_goes_well` section |
| PDP shipping/returns notice copy | `tools/scripts/sync-product.sh` — the `notice_html` string |

## What stays the same

- The crawler (`src/crawl/`) and extractor (`src/extract/`) — they work off
  any standard Shopify storefront sitemap.
- The exec wrapper (`src/admin/exec.ts`) — store-agnostic.
- The validated GraphQL mutations — same Admin schema regardless of store.

## Step-by-step for a new clone

1. **Phase 0 — Bootstrap theme.** Decide the target store + theme ID, push
   Horizon (or another base theme) to the new GitHub repo, connect in admin.
   See [`02-phase-0-bootstrap-theme.md`](./02-phase-0-bootstrap-theme.md).
2. **Update `src/config.ts`** with the new `DEMO_URL`, `TARGET_STORE`,
   `TARGET_THEME_ID`.
3. **Clear caches** (optional but recommended):

   ```sh
   rm -rf tools/.cache tools/data/*.json
   ```

4. **Phase 2 — Crawl** (`pnpm crawl`). Inspect `data/sitemap.json` —
   the printed summary tells you product/collection/page/blog/article counts.
5. **Phase 3 — Extract** (`pnpm extract`). Inspect `data/nav.json` to see what
   menu items the demo actually uses; update the menu blocks in
   `scripts/replicate-content.sh` and `scripts/fix-menus.sh` to match.
6. **Pick collection handles to populate.** Look at the `collection` entries
   in `data/sitemap.json`. Update `TARGET_COLLECTION_HANDLES` in
   `src/admin/sync-collections.ts`.
7. **Update `scripts/replicate-content.sh`** with the right pages, blog,
   collections.
8. **Phase 4 — Auth.** `shopify store auth --store <new-store> --scopes=...`
   See [`06-phase-4-auth.md`](./06-phase-4-auth.md).
9. **Phase 5 — Replicate content.** `bash scripts/replicate-content.sh`.
10. **Phase 6 — Look up the new menu IDs**, paste them into
    `scripts/fix-menus.sh`, run it.
11. **Phase 7 — User uploads products.** Outside this tool.
12. **Phase 8 — Sync collections.** `pnpm sync-collections`.
13. **Document the run.** Per the project's habit, after every major
    milestone update `docs/`. Add or amend numbered phase docs and the
    `docs/README.md` index. (See the `cloner-docs` skill if installed —
    it spells out exactly when to update what.)

## Sanity-check after each phase

| After phase | Quick check                                                      |
| ----------- | ---------------------------------------------------------------- |
| 0           | Theme connected in admin, GitHub sync visible                    |
| 2           | Counts in `Sitemap summary` match what you'd expect from demo    |
| 3           | `data/nav.json` matches the demo's visible header/footer         |
| 4           | `shopify store execute --query 'query { shop { name } }'` works  |
| 5           | Visit `/pages/about-us`, `/blogs/news`, etc. — return 200        |
| 6           | `query { menus(first:25) }` — only `main-menu` and `footer`      |
| 7           | `query { productsCount { count } }` matches demo                 |
| 8           | Visit `/collections/<handle>` — shows expected product count     |

## Hard-coded assumptions that need re-checking

- **Handle alignment between demo and target products.** Phase 8 maps by
  handle; if the new demo has products whose handles won't survive CSV
  import, you'll need an explicit mapping.
- **Menu item URLs are static.** The replicate script hardcodes URLs like
  `/collections/new`. If the new demo's menu links to different paths, edit
  them.
- **Blog handle is `news`.** If the new demo uses a different blog handle,
  update `scripts/replicate-content.sh` and the footer menu's blog link.
- **Footer-group block IDs are theme-instance-specific.** The live
  `sections/footer-group.json` block IDs (`menu_ywDwTf`, `menu_UR3gWa`,
  `menu_4KapTg`) are specific to wear-revamp. New stores will have different
  block IDs. Always read the live file via the `theme.files` query before
  patching.
- **`templates/product.json` may diverge from repo per-store.** Whichever
  preset the new target store has installed (Ritual or otherwise) will write
  its own `templates/product.json` to the live theme, distinct from the
  repo's Horizon default. Always read the live file before patching, and
  match blocks/sections by stable identifiers (block `name` or section
  `type`), never by hard-coded ID.
