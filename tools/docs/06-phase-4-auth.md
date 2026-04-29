# Phase 4 — Shopify CLI auth with required scopes

**Goal:** authorize Shopify CLI to talk to the target store with the full set
of scopes every later phase needs. Doing this once up front means we don't get
"Access denied for X. Required scope: Y" mid-replication.

## The command

```sh
shopify store auth --store wear-revamp.myshopify.com \
  --scopes=read_products,write_products,read_publications,write_publications,write_online_store_navigation,write_content,write_online_store_pages,read_themes,write_themes
```

> ⚠️ **Single line.** If your shell wraps this across newlines without a
> trailing `\`, the CLI parses the second line as a separate command and you
> get `Flag --scopes expects a value`. Use `--scopes=...` (with `=`) on one
> line as shown.

## What each scope unlocks

| Scope                              | Phases that need it                              |
| ---------------------------------- | ------------------------------------------------ |
| `read_products`                    | Phase 8 product handle → GID lookup              |
| `write_products`                   | `collectionAddProducts`                          |
| `read_publications`                | Phase 8 publications query                       |
| `write_publications`               | `publishablePublish`                             |
| `write_online_store_navigation`    | Phase 5 + 6 menu mutations                       |
| `write_content`                    | Phase 5 `blogCreate`                             |
| `write_online_store_pages`         | Phase 5 `pageCreate`                             |
| `read_themes`                      | Phase 9 `theme.files` query                      |
| `write_themes`                     | Phase 9 `themeFilesUpsert` mutation              |

Phase 9 introduced theme-file editing via `themeFilesUpsert`, which is why these two scopes are now in the baseline.

## How auth state is stored

`shopify store auth` opens a browser, you approve the scopes, and the CLI
caches the token under your local Shopify config. Subsequent
`shopify store execute` calls reuse it. Tokens are scoped to the
`--store` you passed, so you can run the same flow against multiple stores
without conflict.

## Re-auth signals

Re-run the same command if you see any of:

- `Access denied for <field>. Required access: <scope>` — your existing token
  is missing a scope. The new scope set replaces the old, so you don't need
  to revoke first.
- `401 Unauthorized` from `shopify store execute` — token expired/revoked.

## Verifying auth

A read-only smoke test:

```sh
shopify store execute --store wear-revamp.myshopify.com \
  --query 'query { shop { name myshopifyDomain } }'
```

Should print:

```json
{ "data": { "shop": { "name": "wear-revamp", "myshopifyDomain": "wear-revamp.myshopify.com" } } }
```
