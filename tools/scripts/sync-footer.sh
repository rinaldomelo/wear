#!/usr/bin/env bash
# Sync the wear-revamp footer to match the Ritual demo's 3-column layout.
# Idempotent: re-running will skip menus that already exist and re-patch the
# theme file deterministically (block lookup is by `heading`, not block id).
#
# Prereqs (run once):
#   shopify store auth --store wear-revamp.myshopify.com \
#     --scopes write_online_store_navigation,write_themes,read_themes
set -euo pipefail

STORE="${STORE:-wear-revamp.myshopify.com}"
THEME_ID="${THEME_ID:-gid://shopify/OnlineStoreTheme/146185617461}"
FOOTER_FILE="sections/footer-group.json"

MENU_LOOKUP_QUERY='query LookupMenu($q: String!) { menus(first: 1, query: $q) { nodes { id handle title } } }'
MENU_CREATE_MUTATION='mutation CreateMenu($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) { menuCreate(title: $title, handle: $handle, items: $items) { menu { id handle } userErrors { code field message } } }'
THEME_READ_QUERY='query GetThemeFile($themeId: ID!, $filename: String!) { theme(id: $themeId) { files(filenames: [$filename]) { nodes { filename body { ... on OnlineStoreThemeFileBodyText { content } } } } } }'
THEME_UPSERT_MUTATION='mutation ThemeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) { themeFilesUpsert(themeId: $themeId, files: $files) { upsertedThemeFiles { filename } userErrors { code field message } } }'

CREATED=0
EXISTED=0

menu_exists() {
  local handle="$1"
  local out
  out=$(shopify store execute --store "$STORE" \
    --query "$MENU_LOOKUP_QUERY" \
    --variables "{\"q\":\"handle:$handle\"}")
  echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); nodes=d['data']['menus']['nodes']; sys.exit(0 if any(n['handle']==\"$handle\" for n in nodes) else 1)"
}

ensure_menu() {
  local title="$1" handle="$2" items_json="$3"
  echo
  echo "→ Ensure menu: $handle"
  if menu_exists "$handle"; then
    echo "  already exists, skipping"
    EXISTED=$((EXISTED + 1))
    return 0
  fi
  # Variables JSON is built in a temp file because the items array is multiline.
  local vars_file
  vars_file=$(mktemp)
  python3 - "$title" "$handle" "$items_json" "$vars_file" <<'PY'
import json, sys
title, handle, items_json, out = sys.argv[1:5]
with open(out, "w") as f:
    json.dump({"title": title, "handle": handle, "items": json.loads(items_json)}, f)
PY
  shopify store execute --store "$STORE" --allow-mutations \
    --query "$MENU_CREATE_MUTATION" \
    --variables "$(cat "$vars_file")"
  rm -f "$vars_file"
  CREATED=$((CREATED + 1))
}

# 1. Menus -----------------------------------------------------------------

ensure_menu "Footer Shop" "footer-shop" '[
  {"title":"Shop all","type":"HTTP","url":"/collections/all","items":[]},
  {"title":"Bestsellers","type":"HTTP","url":"/collections/bestsellers","items":[]},
  {"title":"New arrivals","type":"HTTP","url":"/collections/new","items":[]}
]'

ensure_menu "Footer Brand" "footer-brand" '[
  {"title":"About us","type":"HTTP","url":"/pages/about-us","items":[]},
  {"title":"Blog","type":"HTTP","url":"/blogs/news","items":[]},
  {"title":"Shipping & Returns","type":"HTTP","url":"/pages/shipping-returns","items":[]},
  {"title":"Fit guide","type":"HTTP","url":"/pages/fit-guide","items":[]}
]'

ensure_menu "Footer Connect" "footer-connect" '[
  {"title":"Instagram","type":"HTTP","url":"https://www.instagram.com/","items":[]},
  {"title":"TikTok","type":"HTTP","url":"https://www.tiktok.com/","items":[]},
  {"title":"Facebook","type":"HTTP","url":"https://www.facebook.com/","items":[]},
  {"title":"Contact us","type":"HTTP","url":"/pages/contact","items":[]}
]'

# 2. Read live footer-group.json ------------------------------------------

echo
echo "→ Read $FOOTER_FILE from theme"
READ_VARS=$(mktemp)
python3 - "$THEME_ID" "$FOOTER_FILE" "$READ_VARS" <<'PY'
import json, sys
theme_id, filename, out = sys.argv[1:4]
with open(out, "w") as f:
    json.dump({"themeId": theme_id, "filename": filename}, f)
PY
READ_OUT=$(shopify store execute --store "$STORE" \
  --query "$THEME_READ_QUERY" \
  --variables "$(cat "$READ_VARS")")
rm -f "$READ_VARS"

ORIGINAL=$(mktemp)
echo "$READ_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['data']['theme']['files']['nodes'][0]['body']['content'], end='')" > "$ORIGINAL"

# 3. Patch SHOP/BRAND/CONNECT block menu handles by `heading` -------------

PATCHED=$(mktemp)
MODIFIED=$(python3 - "$ORIGINAL" "$PATCHED" <<'PY'
import re, sys
src, dst = sys.argv[1:3]
with open(src) as f:
    content = f.read()

mapping = {"SHOP": "footer-shop", "BRAND": "footer-brand", "CONNECT": "footer-connect"}

def patch(content, heading, handle):
    # Find the menu key in the block immediately preceding this heading. The
    # block header (id, type, settings) places `menu` before `heading` in the
    # JSON body; we lock the rewrite to within ~600 chars upstream of heading.
    pattern = re.compile(
        r'("menu"\s*:\s*")[^"]*(")(?P<between>(?:(?!"menu"\s*:).){0,600}?"heading"\s*:\s*"' + re.escape(heading) + r'")',
        re.DOTALL,
    )
    return pattern.sub(lambda m: m.group(1) + handle + m.group(2) + m.group("between"), content, count=1)

new_content = content
for h, handle in mapping.items():
    new_content = patch(new_content, h, handle)

with open(dst, "w") as f:
    f.write(new_content)

print("yes" if new_content != content else "no")
PY
)

echo
echo "→ Patch $FOOTER_FILE (modified=$MODIFIED)"

# 4. Upsert patched file --------------------------------------------------

UPSERT_VARS=$(mktemp)
python3 - "$THEME_ID" "$FOOTER_FILE" "$PATCHED" "$UPSERT_VARS" <<'PY'
import json, sys
theme_id, filename, body_path, out = sys.argv[1:5]
with open(body_path) as f:
    body = f.read()
with open(out, "w") as f:
    json.dump({
        "themeId": theme_id,
        "files": [{"filename": filename, "body": {"type": "TEXT", "value": body}}],
    }, f)
PY

echo
echo "→ Upsert $FOOTER_FILE"
shopify store execute --store "$STORE" --allow-mutations \
  --query "$THEME_UPSERT_MUTATION" \
  --variables "$(cat "$UPSERT_VARS")"
rm -f "$UPSERT_VARS"

# 5. Verify ---------------------------------------------------------------

echo
echo "→ Verify heading→menu wiring"
VERIFY_VARS=$(mktemp)
python3 - "$THEME_ID" "$FOOTER_FILE" "$VERIFY_VARS" <<'PY'
import json, sys
theme_id, filename, out = sys.argv[1:4]
with open(out, "w") as f:
    json.dump({"themeId": theme_id, "filename": filename}, f)
PY
VERIFY_OUT=$(shopify store execute --store "$STORE" \
  --query "$THEME_READ_QUERY" \
  --variables "$(cat "$VERIFY_VARS")")
rm -f "$VERIFY_VARS"

echo "$VERIFY_OUT" | python3 -c "
import json, re, sys
d = json.load(sys.stdin)
content = d['data']['theme']['files']['nodes'][0]['body']['content']
for m in re.finditer(r'\"menu\":\s*\"([^\"]*)\"[\s\S]{0,80}?\"heading\":\s*\"([^\"]+)\"', content):
    print(f'  block heading={m.group(2):10}  menu=\"{m.group(1)}\"')
"

rm -f "$ORIGINAL" "$PATCHED"

echo
echo "✓ Footer sync complete. menus created=$CREATED  existed=$EXISTED  file modified=$MODIFIED"
