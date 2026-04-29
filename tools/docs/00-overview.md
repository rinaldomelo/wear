# 00 — Overview

## What this process clones

From a Shopify demo store (Ritual theme) onto a target Shopify dev store
(Horizon theme with Ritual preset already installed):

- **Pages** (placeholder bodies — real bodies are a later phase)
- **A blog** (just the container — articles are a later phase)
- **Collections** (custom/manual, by handle) and product membership
- **Navigation menus** (main + footer)
- **Sales-channel publication** for collections (so they show on the storefront and apps)

## What it deliberately does NOT clone

- **The Horizon theme itself.** The target store already has Horizon installed
  and a Ritual preset applied. We do **not** push `templates/*.json`,
  `config/settings_data.json`, or anything else under the theme root. All
  changes go through the Admin GraphQL API.
- **Products.** The user uploads products separately via a CSV; this tool only
  *attaches* products to collections and publishes them.
- **Page/article HTML bodies.** Pages and the blog are created with placeholder
  bodies. A later step scrapes real bodies from the demo and runs `pageUpdate`.

## Mental model

```
demo storefront                  target store
┌──────────────────┐             ┌──────────────────────────────┐
│ sitemap.xml      │  crawl ──►  │ data/sitemap.json            │
│ /collections/*   │  fetch ──►  │ data/<collection>.handles    │
│ <header>/<footer>│  extract ─► │ data/nav.json                │
│ index.html       │  extract ─► │ data/homepage-sections.json  │
└──────────────────┘             └──────┬───────────────────────┘
                                        │
                                        ▼
                          shopify store execute (GraphQL)
                                        │
                                        ▼
                       ┌──────────────────────────────────┐
                       │ wear-revamp.myshopify.com        │
                       │  • pages, blog, collections      │
                       │  • menus (main, footer)          │
                       │  • collection→product links      │
                       │  • publishablePublish to all     │
                       │    sales channels                │
                       └──────────────────────────────────┘
```

## Why TypeScript + Shopify CLI

- Crawl/extract is plain Node + `cheerio` + `fast-xml-parser` — runs locally.
- Admin writes go through `shopify store execute` (CLI 3.93+) — that means the
  CLI handles auth/refresh, scope grants, and JSON output. We never hand-manage
  an admin token.
- The Shopify AI Toolkit `shopify-admin` skill validates every mutation against
  the live schema before we run it, so we don't burn rate limit on bad shapes.

## Where outputs land

- `tools/data/sitemap.json` — typed graph of demo URLs (products / collections / pages / blogs / articles)
- `tools/data/nav.json` — header + footer link lists scraped from the demo
- `tools/data/homepage-sections.json` — Ritual section IDs in homepage order, mapped to Horizon equivalents
- `tools/.cache/<sha1>` — cached HTML/JSON responses from the demo for polite re-runs
