# Shopify Demo Cloner — Playbook

This `docs/` folder captures the end-to-end process we used to clone the
[theme-ritual-demo](https://theme-ritual-demo.myshopify.com/) store onto
`wear-revamp.myshopify.com` using the Horizon theme. It is written so the same
flow can be re-run against a **different** demo store and target store with
minimal edits.

## Read in order

1. [`00-overview.md`](./00-overview.md) — what this clones, what it does not, mental model
2. [`01-prerequisites.md`](./01-prerequisites.md) — tools, accounts, scopes
3. [`02-phase-0-bootstrap-theme.md`](./02-phase-0-bootstrap-theme.md) — push Horizon to GitHub, connect to target store
4. [`03-phase-1-scaffold-tools.md`](./03-phase-1-scaffold-tools.md) — workspace layout under `tools/`
5. [`04-phase-2-crawl.md`](./04-phase-2-crawl.md) — sitemap walk → `data/sitemap.json`
6. [`05-phase-3-extract.md`](./05-phase-3-extract.md) — nav + homepage sections
7. [`06-phase-4-auth.md`](./06-phase-4-auth.md) — `shopify store auth` with required scopes
8. [`07-phase-5-replicate-content.md`](./07-phase-5-replicate-content.md) — pages, blog, collections, menus via Admin GraphQL
9. [`08-phase-6-fix-menus.md`](./08-phase-6-fix-menus.md) — handle the default menu collision
10. [`09-phase-7-products.md`](./09-phase-7-products.md) — user-uploaded product CSV step
11. [`10-phase-8-sync-collections.md`](./10-phase-8-sync-collections.md) — populate collections + publish to all sales channels
12. [`14-phase-9-match-footer-header.md`](./14-phase-9-match-footer-header.md) — wire footer menu blocks to dedicated menus
13. [`15-phase-10-product-page.md`](./15-phase-10-product-page.md) — patch `templates/product.json` to match the demo PDP
14. [`16-phase-11-audit-collections.md`](./16-phase-11-audit-collections.md) — audit collection ↔ product links, fix the empty `accessories` collection
15. [`17-phase-12-home-page.md`](./17-phase-12-home-page.md) — patch `templates/index.json` to match the demo home (wire collection-list grid, featured product, replace 2nd carousel with layered-slideshow)
16. [`11-next-steps.md`](./11-next-steps.md) — pending two-step continuations (page bodies, collection metadata)
17. [`12-troubleshooting.md`](./12-troubleshooting.md) — errors we hit and how we fixed them
18. [`13-reusing-for-another-site.md`](./13-reusing-for-another-site.md) — diff checklist when pointing at a new demo/target

## Snapshot of the live run

- **Demo:** `https://theme-ritual-demo.myshopify.com/`
- **Target:** `wear-revamp.myshopify.com` (currently published theme `146185682997`, Ritual preset on Horizon)
- **Repo:** `https://github.com/rinaldomelo/wear` (Horizon at root, cloner under `tools/`, branch `main` is the source of truth — repo is kept in sync with live)
- **Result so far:** 4 pages + 1 blog + 8 collections + 2 menus created; 71 products uploaded by user; collections fully populated and audited — every target collection's live product set matches the demo's set 1:1 (`new` 30, `tops` 17, `bottoms` 30, `knitwear` 7, `dresses` 6, `denim` 20, `accessories` 4, `bestsellers` 39 — 153 links total) and published to all 3 sales channels; footer rebuilt with 3 column menus (SHOP/BRAND/CONNECT) wired into theme via themeFilesUpsert; product page brought to demo parity (single Add to cart, static "Goes well with..." row of 6 collections, dark text-only collection-links bar above the footer wired to those same 6 collections, Wear shipping/returns notice); home page brought to demo parity (collection-list grid wired to knitwear/dresses/denim/bottoms, featured-product set to rose-11-bag-1, second carousel replaced with a 3-slide layered-slideshow ingested from the demo CDN).
