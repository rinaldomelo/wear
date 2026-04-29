# 01 — Prerequisites

## CLI / runtime

| Tool          | Min version | Why                                          |
| ------------- | ----------- | -------------------------------------------- |
| Shopify CLI   | **3.93.0**  | `shopify store auth` / `shopify store execute` were added here |
| Node.js       | 20+ (used 25.2) | Native `fetch`, ES modules                |
| pnpm          | 10+ (used 10.33) | Workspace package manager                |
| `gh` (GitHub) | 2.80+       | Push the Horizon bootstrap commit            |
| git           | any modern  | History reset + push                         |

Verify:

```sh
shopify version
node -v
pnpm -v
gh --version
```

If `shopify store execute` errors with "unknown command", upgrade the CLI:

```sh
brew upgrade shopify-cli         # macOS Homebrew
# or: npm i -g @shopify/cli@latest
```

## Accounts / access

- **GitHub** account with permission to push to the target empty repo
  (we used `https://github.com/rinaldomelo/wear`).
- **Shopify Partner / Plus dev store** with admin access to the target store
  (we used `wear-revamp.myshopify.com`). The user must be able to:
  - Connect a GitHub repo to a theme in *Online Store → Themes*.
  - Authorize CLI scopes via `shopify store auth`.

## Skills used (Claude side)

These come from the `shopify-ai-toolkit` plugin and run locally:

- `shopify-admin` — searches Admin API docs, validates GraphQL with `validate.mjs` before we run anything
- `shopify-admin-execution` — wraps validated ops as `shopify store auth` + `shopify store execute` commands

You don't need them to be installed by name; they auto-load when the user types relevant questions in Claude Code with the plugin enabled.

## Required Admin API scopes

We grant a single broad-but-bounded set up front so we don't have to re-auth between phases:

```
read_products,write_products,
read_publications,write_publications,
write_online_store_navigation,
write_content,
write_online_store_pages
```

| Scope                              | Used by                                          |
| ---------------------------------- | ------------------------------------------------ |
| `read_products` / `write_products` | products query, `collectionAddProducts`          |
| `read_publications` / `write_publications` | `publications` query, `publishablePublish` |
| `write_online_store_navigation`    | `menuCreate`, `menuUpdate`, `menuDelete`         |
| `write_content`                    | `blogCreate`                                     |
| `write_online_store_pages`         | `pageCreate`                                     |

If you want to support page-body updates and collection hero images later, add `write_files` and `write_themes` (or stick to `write_content` only — most of the page/blog write surface lives there).

## Directory layout assumed by every phase

```
/Users/melo/clone-shopify/                # repo root (Horizon theme files at root)
├── assets/  blocks/  config/ ...         # Horizon files — DO NOT touch
└── tools/                                # this cloner
    ├── package.json
    ├── tsconfig.json
    ├── src/                              # crawl/extract/admin sources
    ├── scripts/                          # bash glue (auth + content replication)
    ├── data/                             # crawl outputs (gitignored except .gitkeep)
    └── docs/                             # this folder
```
