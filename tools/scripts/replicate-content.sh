#!/usr/bin/env bash
# Replicate the theme-ritual-demo content onto wear-revamp via Shopify Admin GraphQL.
# Theme 146185617461 (Ritual preset) is NOT touched. This only creates pages, blog, collections, menus.
#
# Prereqs (run once):
#   shopify store auth --store wear-revamp.myshopify.com \
#     --scopes write_content,write_online_store_pages,write_products,write_online_store_navigation
set -euo pipefail

STORE="wear-revamp.myshopify.com"

execute() {
  local label="$1"
  local query="$2"
  local variables="$3"
  echo
  echo "→ $label"
  shopify store execute \
    --store "$STORE" \
    --allow-mutations \
    --query "$query" \
    --variables "$variables"
}

PAGE_MUTATION='mutation CreatePage($page: PageCreateInput!) { pageCreate(page: $page) { page { id title handle } userErrors { code field message } } }'
BLOG_MUTATION='mutation CreateBlog($blog: BlogCreateInput!) { blogCreate(blog: $blog) { blog { id title handle commentPolicy } userErrors { code field message } } }'
COLLECTION_MUTATION='mutation CollectionCreate($input: CollectionInput!) { collectionCreate(input: $input) { collection { id title handle } userErrors { field message } } }'
MENU_MUTATION='mutation CreateMenu($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) { menuCreate(title: $title, handle: $handle, items: $items) { menu { id handle title items { id title type url } } userErrors { code field message } } }'

# 1. Pages -----------------------------------------------------------------
PAGE_BODY='<p>Placeholder copy — fill in via the Shopify admin or rerun with extracted demo content.</p>'

create_page() {
  local title="$1" handle="$2"
  execute "Create page: $title" "$PAGE_MUTATION" \
    "{\"page\":{\"title\":\"$title\",\"handle\":\"$handle\",\"body\":\"$PAGE_BODY\",\"isPublished\":true}}"
}

create_page "About Us"            "about-us"
create_page "Contact"             "contact"
create_page "Fit Guide"           "fit-guide"
create_page "Shipping & Returns"  "shipping-returns"

# 2. Blog ------------------------------------------------------------------
execute "Create blog: News" "$BLOG_MUTATION" \
  '{"blog":{"title":"News","handle":"news","commentPolicy":"MODERATED"}}'

# 3. Collections (custom / manual) -----------------------------------------
create_collection() {
  local title="$1" handle="$2"
  execute "Create collection: $title" "$COLLECTION_MUTATION" \
    "{\"input\":{\"title\":\"$title\",\"handle\":\"$handle\"}}"
}

create_collection "New"          "new"
create_collection "Tops"         "tops"
create_collection "Bottoms"      "bottoms"
create_collection "Knitwear"     "knitwear"
create_collection "Dresses"      "dresses"
create_collection "Denim"        "denim"
create_collection "Accessories"  "accessories"
create_collection "Bestsellers"  "bestsellers"

# 4. Menus -----------------------------------------------------------------
# Note: type=COLLECTION/PAGE/BLOG with a `url` and no resourceId works for new
# stores that don't yet have those resources GIDs handy. Shopify resolves the
# url to the resource by handle on render. We use HTTP type for safety here.

execute "Create main-menu" "$MENU_MUTATION" '{
  "title": "Main menu",
  "handle": "main-menu",
  "items": [
    { "title": "New",     "type": "HTTP", "url": "/collections/new",     "items": [] },
    { "title": "Tops",    "type": "HTTP", "url": "/collections/tops",    "items": [] },
    { "title": "Bottoms", "type": "HTTP", "url": "/collections/bottoms", "items": [] }
  ]
}'

execute "Create footer menu" "$MENU_MUTATION" '{
  "title": "Footer",
  "handle": "footer",
  "items": [
    { "title": "Shop all",           "type": "HTTP", "url": "/collections/all",          "items": [] },
    { "title": "Bestsellers",        "type": "HTTP", "url": "/collections/bestsellers",  "items": [] },
    { "title": "New arrivals",       "type": "HTTP", "url": "/collections/new",          "items": [] },
    { "title": "About us",           "type": "HTTP", "url": "/pages/about-us",           "items": [] },
    { "title": "Blog",               "type": "HTTP", "url": "/blogs/news",               "items": [] },
    { "title": "Shipping & Returns", "type": "HTTP", "url": "/pages/shipping-returns",   "items": [] },
    { "title": "Fit guide",          "type": "HTTP", "url": "/pages/fit-guide",          "items": [] },
    { "title": "Contact us",         "type": "HTTP", "url": "/pages/contact",            "items": [] }
  ]
}'

echo
echo "✓ Replication complete."
