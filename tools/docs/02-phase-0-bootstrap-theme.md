# Phase 0 — Bootstrap the theme repo

**Goal:** stand up an empty GitHub repo containing Shopify's Horizon theme at
the root, then connect that repo to the target store's existing theme via
GitHub. After this phase the user owns a theme on the target store that auto-
syncs from `main`.

> Do this **once** per target store. After the GitHub connection is made,
> you don't push theme changes from here again — content replication uses
> the Admin API only.

## Inputs you need

| Input               | Example                                          |
| ------------------- | ------------------------------------------------ |
| Empty target repo   | `https://github.com/rinaldomelo/wear.git`        |
| Target store        | `wear-revamp.myshopify.com`                      |
| Existing theme ID   | `146185617461`                                   |

## Steps

```sh
cd /Users/melo/clone-shopify    # must be empty or only .git/

# 1. Pull Horizon source
git clone https://github.com/Shopify/horizon.git .

# 2. Reset history so this becomes a clean root commit on YOUR repo
rm -rf .git
git init -b main
git remote add origin https://github.com/<owner>/<repo>.git
git add -A
git commit -m "chore: bootstrap from Shopify/horizon"
git push -u origin main
```

## Manual step in Shopify admin

1. Go to *Online Store → Themes* on the target store.
2. Open the theme `<theme ID>` (the one you want to track).
3. Click *Add from GitHub* and pick the repo + branch (`main`).
4. Confirm the connection — Shopify will pull the theme from GitHub.

## Why we keep the theme alone after this

The target store's theme already has a **preset applied** (in our case Ritual).
Pushing template JSON or `settings_data.json` from here would clobber that
preset. Every later phase touches Admin API resources only — collections,
products, pages, menus, etc.

## Where the cloner lives

After this push, we add a sibling `tools/` directory **alongside** the Horizon
files. The Horizon files stay at the repo root so the GitHub connection keeps
working. See [Phase 1](./03-phase-1-scaffold-tools.md).
