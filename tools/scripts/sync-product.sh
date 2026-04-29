#!/usr/bin/env bash
# Sync the wear-revamp product page (templates/product.json) to match the
# Ritual demo:
#   - drop the accelerated-checkout (Shop Pay) block from buy-buttons
#   - replace `product-recommendations` with a static `collection-list` of
#     6 collections (Bestsellers, Dresses, Tops, Accessories, Bottoms, Denim)
#   - drop the unused `collection-links` section the preset left behind
#   - add a small Wear-branded shipping/returns notice under buy-buttons
#
# Idempotent: detects the already-patched shape and short-circuits the upsert.
#
# Prereqs (run once):
#   shopify store auth --store wear-revamp.myshopify.com \
#     --scopes write_themes,read_themes
set -euo pipefail

STORE="${STORE:-wear-revamp.myshopify.com}"
THEME_ID="${THEME_ID:-gid://shopify/OnlineStoreTheme/146185617461}"
PRODUCT_FILE="templates/product.json"

THEME_READ_QUERY='query GetThemeFile($themeId: ID!, $filename: String!) { theme(id: $themeId) { files(filenames: [$filename]) { nodes { filename body { ... on OnlineStoreThemeFileBodyText { content } } } } } }'
THEME_UPSERT_MUTATION='mutation ThemeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) { themeFilesUpsert(themeId: $themeId, files: $files) { upsertedThemeFiles { filename } userErrors { code field message } } }'

# 1. Read live templates/product.json --------------------------------------

echo "→ Read $PRODUCT_FILE from theme"
READ_VARS=$(mktemp)
python3 - "$THEME_ID" "$PRODUCT_FILE" "$READ_VARS" <<'PY'
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
echo "$READ_OUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
inner = d.get('data', d)
print(inner['theme']['files']['nodes'][0]['body']['content'], end='')
" > "$ORIGINAL"

# 2. Patch in memory -------------------------------------------------------

PATCHED=$(mktemp)
STATUS=$(python3 - "$ORIGINAL" "$PATCHED" <<'PY'
import json, re, sys

src, dst = sys.argv[1:3]
with open(src) as f:
    raw = f.read()

# Preserve the `/* auto-generated */` comment header that Shopify stamps.
m = re.match(r'(/\*[\s\S]*?\*/\s*)', raw)
header = m.group(1) if m else ''
body = raw[len(header):]
data = json.loads(body)

sections = data["sections"]
order = data["order"]

main = sections["main"]
product_details = main["blocks"]["product-details"]
buy_buttons = product_details["blocks"]["buy_buttons"]

# (a) drop accelerated-checkout from buy_buttons
removed_accel = "accelerated-checkout" in buy_buttons["blocks"]
buy_buttons["blocks"].pop("accelerated-checkout", None)
if "block_order" in buy_buttons:
    buy_buttons["block_order"] = [b for b in buy_buttons["block_order"] if b != "accelerated-checkout"]

# (b) add a Wear shipping & returns notice text block under product-details,
#     positioned right after the description.
notice_id = "text_wear_notice"
notice_html = "<p>Free shipping over $75 &middot; 30-day returns</p>"
notice_block = {
    "type": "text",
    "name": "Shipping & returns notice",
    "settings": {
        "text": notice_html,
        "width": "100%",
        "max_width": "normal",
        "alignment": "left",
        "type_preset": "paragraph",
        "font": "var(--font-body--family)",
        "font_size": "0.875rem",
        "line_height": "normal",
        "letter_spacing": "normal",
        "case": "none",
        "wrap": "pretty",
        "color": "var(--color-foreground-subdued)",
        "background": False,
        "background_color": "#00000026",
        "corner_radius": 0,
        "padding-block-start": 8,
        "padding-block-end": 0,
        "padding-inline-start": 0,
        "padding-inline-end": 0,
    },
    "blocks": {},
}
added_notice = notice_id not in product_details["blocks"]
product_details["blocks"][notice_id] = notice_block

# Insert after the description block in block_order. The Ritual preset uses id
# "text" for the description. Repo uses "text_aEtTtq". Match by id substring.
po = product_details.get("block_order", [])
if notice_id in po:
    po = [b for b in po if b != notice_id]
desc_idx = next((i for i, b in enumerate(po) if b == "text" or b.startswith("text_")), len(po) - 1)
po.insert(desc_idx + 1, notice_id)
product_details["block_order"] = po

# (c) replace `product-recommendations` (or `product_recommendations_*`) with
#     a static collection-list of 6 demo collections.
goes_well_id = "collection_list_goes_well"
removed_recos = False
for sid in list(sections.keys()):
    if sid == "product-recommendations" or sid.startswith("product_recommendations"):
        sections.pop(sid)
        removed_recos = True
        order = [s for s in order if s != sid]

# (d) drop the unused collection-links section the preset stamped in.
removed_collinks = False
for sid in list(sections.keys()):
    if sections[sid].get("type") == "collection-links":
        sections.pop(sid)
        order = [s for s in order if s != sid]
        removed_collinks = True

# (e) add the new collection-list section.
collection_list_section = {
    "type": "collection-list",
    "name": "Goes well with",
    "blocks": {
        "header_text": {
            "type": "text",
            "name": "Heading",
            "settings": {
                "text": "<h3>Goes well with...</h3>",
                "width": "fit-content",
                "max_width": "normal",
                "alignment": "left",
                "type_preset": "h2",
                "font": "var(--font-primary--family)",
                "font_size": "",
                "line_height": "normal",
                "letter_spacing": "normal",
                "case": "none",
                "wrap": "pretty",
                "color": "",
                "background": False,
                "background_color": "#00000026",
                "corner_radius": 0,
                "padding-block-start": 0,
                "padding-block-end": 16,
                "padding-inline-start": 0,
                "padding-inline-end": 0,
            },
            "blocks": {},
        },
        "static-collection-card": {
            "type": "_collection-card",
            "name": "t:names.collection_card",
            "static": True,
            "settings": {
                "horizontal_alignment": "flex-start",
                "vertical_alignment": "center",
                "placement": "below_image",
                "inherit_color_scheme": True,
                "color_scheme": "",
                "border": "none",
                "border_width": 1,
                "border_opacity": 100,
                "border_radius": 0,
            },
            "blocks": {
                "collection-card-image": {
                    "type": "_collection-card-image",
                    "name": "t:names.collection_card_image",
                    "static": True,
                    "settings": {"image_ratio": "adapt"},
                    "blocks": {},
                },
                "collection-title": {
                    "type": "collection-title",
                    "name": "t:names.collection_title",
                    "settings": {
                        "type_preset": "rte",
                        "font": "var(--font-body--family)",
                        "font_size": "",
                        "line_height": "normal",
                        "letter_spacing": "normal",
                        "case": "none",
                        "wrap": "pretty",
                        "color": "var(--color-foreground)",
                        "alignment": "left",
                    },
                    "blocks": {},
                },
            },
            "block_order": ["collection-title"],
        },
    },
    "block_order": ["header_text"],
    "settings": {
        "collection_list": ["bestsellers", "dresses", "tops", "accessories", "bottoms", "denim"],
        "layout_type": "grid",
        "carousel_on_mobile": False,
        "columns": 6,
        "mobile_columns": "2",
        "columns_gap": 12,
        "rows_gap": 12,
        "icons_style": "arrow",
        "icons_shape": "none",
        "section_width": "page-width",
        "gap": 24,
        "color_scheme": "scheme-1",
        "padding-block-start": 48,
        "padding-block-end": 48,
    },
}
sections[goes_well_id] = collection_list_section
if goes_well_id not in order:
    order.append(goes_well_id)

# (f) final order: just main + the new collection list.
data["order"] = ["main"] + [s for s in order if s != "main"]

# Serialize back, preserving the header.
new_body = json.dumps(data, indent=2, ensure_ascii=False)
out = header + new_body + "\n"

# Idempotency check: only flag "modified" if anything actually changed.
modified = (out != raw)

with open(dst, "w") as f:
    f.write(out)

print(json.dumps({
    "modified": modified,
    "removed_accel": removed_accel,
    "removed_recos": removed_recos,
    "removed_collinks": removed_collinks,
    "added_notice": added_notice,
}))
PY
)

echo "  status: $STATUS"

# 3. Upsert ----------------------------------------------------------------

UPSERT_VARS=$(mktemp)
python3 - "$THEME_ID" "$PRODUCT_FILE" "$PATCHED" "$UPSERT_VARS" <<'PY'
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
echo "→ Upsert $PRODUCT_FILE"
shopify store execute --store "$STORE" --allow-mutations \
  --query "$THEME_UPSERT_MUTATION" \
  --variables "$(cat "$UPSERT_VARS")"
rm -f "$UPSERT_VARS"

# 4. Verify ----------------------------------------------------------------

echo
echo "→ Verify by re-reading"
VERIFY_VARS=$(mktemp)
python3 - "$THEME_ID" "$PRODUCT_FILE" "$VERIFY_VARS" <<'PY'
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
inner = d.get('data', d)
content = inner['theme']['files']['nodes'][0]['body']['content']
content = re.sub(r'^/\*[\s\S]*?\*/\s*', '', content)
data = json.loads(content)
sections = data['sections']
print(f\"  order:         {data['order']}\")
print(f\"  has accelerated-checkout: {'accelerated-checkout' in sections.get('main', {}).get('blocks', {}).get('product-details', {}).get('blocks', {}).get('buy_buttons', {}).get('blocks', {})}\")
goes = sections.get('collection_list_goes_well', {})
print(f\"  collection-list section: type={goes.get('type', 'MISSING')}\")
print(f\"  collection_list:         {goes.get('settings', {}).get('collection_list', 'MISSING')}\")
print(f\"  product-recommendations: {[k for k in sections if 'recommendation' in k]}\")
print(f\"  collection-links:        {[k for k,v in sections.items() if isinstance(v, dict) and v.get('type') == 'collection-links']}\")
"

rm -f "$ORIGINAL" "$PATCHED"

echo
echo "✓ Product page sync complete."
