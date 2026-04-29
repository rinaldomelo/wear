# 11 — Next steps (planned, not yet implemented)

After Phase 8 the target store has working URLs, populated collections, and
correct nav. Pages and the blog still hold placeholder bodies. Below are the
next two-step increments we sketched out with the user.

## Step A — Real page bodies

**Goal:** scrape the demo's actual HTML for About Us, Contact, Fit Guide,
Shipping & Returns, then `pageUpdate` on the target.

Plan:

1. New file `src/extract/page-bodies.ts`:
   - Fetch `${DEMO_URL}/pages/${handle}` for each page handle.
   - Extract the *content region* — typically `<main>` minus header/footer
     wrappers — using cheerio.
   - Sanitize: drop scripts/styles, rewrite Shopify CDN image URLs (we'll
     either keep them pointing at the demo CDN, or download + re-upload via
     `stagedUploadsCreate` in a follow-up).
   - Persist as `data/page-bodies.json` keyed by handle.
2. New file `src/admin/sync-page-bodies.ts`:
   - Read `data/page-bodies.json`.
   - For each handle, find the target page by handle (`pageByHandle`).
   - Run `pageUpdate` with the cleaned HTML.
3. New CLI command `pnpm sync-page-bodies` wired in `src/cli.ts`.

GraphQL we'll need (validate before running):

```graphql
query PageByHandle($handle: String!) {
  pageByHandle(handle: $handle) { id handle }
}

mutation PageUpdate($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) {
    page { id handle }
    userErrors { code field message }
  }
}
```

## Step B — Collection metadata

**Goal:** pull each demo collection's `descriptionHtml` and hero image, then
`collectionUpdate` on the target.

Plan:

1. Extract `description` + main image URL from each `${DEMO_URL}/collections/${handle}` page.
2. For images, choose between:
   - **Quick:** keep demo CDN URLs as `image.src` (works because Shopify CDN
     URLs are public).
   - **Owned:** download → `stagedUploadsCreate` → reference the new
     `mediaContentType: IMAGE` URL.
3. `collectionUpdate(input: { id, descriptionHtml, image: { src } })` per collection.

## How to slot more steps in

Each new "step" should:

1. Read inputs from `data/*.json` (extracted) and the live target store (queries).
2. Validate every mutation with the `shopify-admin` skill **before** running it.
3. Wrap the runnable workflow in either a new `src/admin/*.ts` plus a CLI
   subcommand, or a one-shot `scripts/*.sh` if it's truly one-time.
4. Add a doc page under `docs/` (numbered) and link it from `docs/README.md`.

See [`13-reusing-for-another-site.md`](./13-reusing-for-another-site.md) for the
checklist when changing sites.
