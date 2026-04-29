# Phase 6 — Reconcile the default menu collision

**Goal:** make the storefront use the menu items we want under the *original*
`main-menu` and `footer` handles, and delete the duplicate menus that Phase 5
created.

## Why this is a separate phase

Shopify creates two menus on every new store:

- `main-menu` (id varies per store)
- `footer` (id varies per store)

Their handles are reserved/protected. When Phase 5's `menuCreate` ran with
`handle: "main-menu"`, Shopify accepted it but suffixed the handle on the new
record:

| Phase 5 created      | Actual handle on storefront |
| -------------------- | --------------------------- |
| handle `main-menu`   | `main-menu-1`               |
| handle `footer`      | `footer-1`                  |

The theme's header/footer Liquid references `main-menu` and `footer`. So we
have two options:

1. **Update the defaults** with our items → delete the suffixed duplicates.
   *(What we did. Cleanest result.)*
2. Update the theme's section settings to point to `main-menu-1` / `footer-1`.
   *(Avoid — couples theme to migration history.)*

## The script

`scripts/fix-menus.sh` does option 1.

> ⚠️ **Menu IDs are store-specific.** The IDs hardcoded in this script
> (`gid://shopify/Menu/231044186165`, etc.) belong to *wear-revamp*. For a new
> store you must look up your own IDs first.

### Look up the menu IDs

```sh
shopify store execute --store <your-store>.myshopify.com \
  --query 'query { menus(first: 25) { nodes { id handle title } } }'
```

Pick out:

- the `id` for handle `main-menu` (default)
- the `id` for handle `footer` (default)
- the `id` for handle `main-menu-1` (Phase 5 duplicate, to delete)
- the `id` for handle `footer-1` (Phase 5 duplicate, to delete)

Paste them into the four `*_ID` variables at the top of `scripts/fix-menus.sh`.

### Run

```sh
bash scripts/fix-menus.sh
```

The script issues four mutations:

1. `menuUpdate` on default `main-menu` with our items
2. `menuUpdate` on default `footer` with our items
3. `menuDelete` on `main-menu-1`
4. `menuDelete` on `footer-1`

## Mutations used

```graphql
mutation UpdateMenu($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id handle title items { id title type url } }
    userErrors { code field message }
  }
}

mutation DeleteMenu($id: ID!) {
  menuDelete(id: $id) {
    deletedMenuId
    userErrors { code field message }
  }
}
```

## Verify

```sh
shopify store execute --store <your-store>.myshopify.com \
  --query 'query { menus(first: 25) { nodes { handle title items { title type url } } } }'
```

You should see exactly two menus, with handles `main-menu` and `footer`, each
populated with the correct items. The storefront header/footer should now
match the demo.
