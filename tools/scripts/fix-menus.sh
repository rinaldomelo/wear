#!/usr/bin/env bash
# Replace the items on the default main-menu and footer menus with our nav,
# then delete the duplicate main-menu-1 / footer-1 created earlier.
set -euo pipefail

STORE="wear-revamp.myshopify.com"

MAIN_MENU_ID="gid://shopify/Menu/231044186165"      # default main-menu
FOOTER_MENU_ID="gid://shopify/Menu/231044218933"    # default footer
DUP_MAIN_ID="gid://shopify/Menu/231044612149"       # main-menu-1 (delete)
DUP_FOOTER_ID="gid://shopify/Menu/231044644917"     # footer-1 (delete)

UPDATE_MUTATION='mutation UpdateMenu($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) { menuUpdate(id: $id, title: $title, items: $items) { menu { id handle title items { id title type url } } userErrors { code field message } } }'
DELETE_MUTATION='mutation DeleteMenu($id: ID!) { menuDelete(id: $id) { deletedMenuId userErrors { code field message } } }'

echo
echo "→ Update default main-menu (handle: main-menu)"
shopify store execute --store "$STORE" --allow-mutations \
  --query "$UPDATE_MUTATION" \
  --variables "{
    \"id\": \"$MAIN_MENU_ID\",
    \"title\": \"Main menu\",
    \"items\": [
      { \"title\": \"New\",     \"type\": \"HTTP\", \"url\": \"/collections/new\",     \"items\": [] },
      { \"title\": \"Tops\",    \"type\": \"HTTP\", \"url\": \"/collections/tops\",    \"items\": [] },
      { \"title\": \"Bottoms\", \"type\": \"HTTP\", \"url\": \"/collections/bottoms\", \"items\": [] }
    ]
  }"

echo
echo "→ Update default footer (handle: footer)"
shopify store execute --store "$STORE" --allow-mutations \
  --query "$UPDATE_MUTATION" \
  --variables "{
    \"id\": \"$FOOTER_MENU_ID\",
    \"title\": \"Footer\",
    \"items\": [
      { \"title\": \"Shop all\",           \"type\": \"HTTP\", \"url\": \"/collections/all\",          \"items\": [] },
      { \"title\": \"Bestsellers\",        \"type\": \"HTTP\", \"url\": \"/collections/bestsellers\",  \"items\": [] },
      { \"title\": \"New arrivals\",       \"type\": \"HTTP\", \"url\": \"/collections/new\",          \"items\": [] },
      { \"title\": \"About us\",           \"type\": \"HTTP\", \"url\": \"/pages/about-us\",           \"items\": [] },
      { \"title\": \"Blog\",               \"type\": \"HTTP\", \"url\": \"/blogs/news\",               \"items\": [] },
      { \"title\": \"Shipping & Returns\", \"type\": \"HTTP\", \"url\": \"/pages/shipping-returns\",   \"items\": [] },
      { \"title\": \"Fit guide\",          \"type\": \"HTTP\", \"url\": \"/pages/fit-guide\",          \"items\": [] },
      { \"title\": \"Contact us\",         \"type\": \"HTTP\", \"url\": \"/pages/contact\",            \"items\": [] }
    ]
  }"

echo
echo "→ Delete duplicate main-menu-1"
shopify store execute --store "$STORE" --allow-mutations \
  --query "$DELETE_MUTATION" \
  --variables "{\"id\": \"$DUP_MAIN_ID\"}"

echo
echo "→ Delete duplicate footer-1"
shopify store execute --store "$STORE" --allow-mutations \
  --query "$DELETE_MUTATION" \
  --variables "{\"id\": \"$DUP_FOOTER_ID\"}"

echo
echo "✓ Menus reconciled."
