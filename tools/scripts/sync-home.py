#!/usr/bin/env python3
"""Phase 12 — bring templates/index.json on wear-revamp to demo parity.

Pattern: read live → patch in memory → themeFilesUpsert → pull back into repo.

What it does:
  1. Uploads the 3 demo slideshow images into wear-revamp's Files via fileCreate
     (Shopify ingests them from the demo CDN on its own).
  2. Wires the existing collection_list_FFV7jq grid to the 4 demo handles.
  3. Sets featured_product_pW7dEU.product to "rose-11-bag-1".
  4. Removes the second collection-list section (collection_list_iAQiBH) — the
     demo doesn't have a second one.
  5. Inserts a layered_slideshow_A6t8QQ section with 3 slides (heading + body
     + button + bg image), matching the demo content.
  6. Updates `order` to [logo, collection-list, featured-product, product-list,
     layered-slideshow, marquee].

Idempotent: re-running with the live file already patched is a no-op.
"""
import json
import os
import re
import subprocess
import sys
import time

STORE = "wear-revamp.myshopify.com"
THEME_ID = "gid://shopify/OnlineStoreTheme/146185682997"
REPO_ROOT = "/Users/melo/clone-shopify"
TEMPLATE_PATH = "templates/index.json"

DEMO_IMAGES = [
    {
        "url": "https://theme-ritual-demo.myshopify.com/cdn/shop/files/79.webp?v=1746499915",
        "alt": "Rise to the top — tops collection slide",
    },
    {
        "url": "https://theme-ritual-demo.myshopify.com/cdn/shop/files/Untitled_design.webp?v=1746499648",
        "alt": "Iconic for a reason — bestsellers slide",
    },
    {
        "url": "https://theme-ritual-demo.myshopify.com/cdn/shop/files/251108_SEENUSERS_CK_15_094_F2C.jpg?v=1765564247",
        "alt": "Fashion forward — new arrivals slide",
    },
]

GRID_HANDLES = ["knitwear", "dresses", "denim", "bottoms"]
FEATURED_PRODUCT_HANDLE = "rose-11-bag-1"


def shopify_exec(query, variables=None, allow_mutations=False):
    args = ["shopify", "store", "execute", "--store", STORE, "--query", query]
    if variables is not None:
        args += ["--variables", json.dumps(variables)]
    if allow_mutations:
        args += ["--allow-mutations"]
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"CLI error (rc={res.returncode}):\n{res.stderr[-1500:]}", file=sys.stderr)
        sys.exit(1)
    out = res.stdout.strip()
    i = out.find("{")
    if i > 0:
        out = out[i:]
    d = json.loads(out)
    return d.get("data", d)


def read_live_template():
    q = """query GetThemeFile($themeId: ID!, $filename: String!) {
      theme(id: $themeId) {
        files(filenames: [$filename]) {
          nodes {
            filename
            body { ... on OnlineStoreThemeFileBodyText { content } }
          }
        }
      }
    }"""
    res = shopify_exec(q, {"themeId": THEME_ID, "filename": TEMPLATE_PATH})
    nodes = res["theme"]["files"]["nodes"]
    if not nodes:
        print(f"templates/index.json not found on theme {THEME_ID}", file=sys.stderr)
        sys.exit(1)
    return nodes[0]["body"]["content"]


def write_template(content):
    q = """mutation ThemeFilesUpsert($themeId: ID!, $files: [OnlineStoreThemeFilesUpsertFileInput!]!) {
      themeFilesUpsert(themeId: $themeId, files: $files) {
        upsertedThemeFiles { filename }
        userErrors { code field message }
      }
    }"""
    variables = {
        "themeId": THEME_ID,
        "files": [{"filename": TEMPLATE_PATH, "body": {"type": "TEXT", "value": content}}],
    }
    res = shopify_exec(q, variables, allow_mutations=True)
    errs = res["themeFilesUpsert"].get("userErrors") or []
    if errs:
        print(f"themeFilesUpsert errors: {errs}", file=sys.stderr)
        sys.exit(1)
    print(f"  upserted: {res['themeFilesUpsert']['upsertedThemeFiles']}")


def find_existing_images_by_alt(alts):
    """Return a list of MediaImage GIDs (parallel to `alts`) if every alt
    matches an existing READY file. Otherwise return None."""
    q = """query Files($cursor: String) {
      files(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { ... on MediaImage { id alt fileStatus } }
      }
    }"""
    by_alt = {}
    cursor = None
    for _ in range(10):
        res = shopify_exec(q, {"cursor": cursor})
        page = res["files"]
        for n in page["nodes"]:
            if n and n.get("alt") and n.get("fileStatus") == "READY":
                by_alt[n["alt"]] = n["id"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    matches = [by_alt.get(a) for a in alts]
    if all(matches):
        return matches
    return None


def upload_image(url, alt):
    """fileCreate from a public URL. Returns the MediaImage GID once READY."""
    q = """mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { id alt fileStatus ... on MediaImage { image { url } } }
        userErrors { field message }
      }
    }"""
    variables = {"files": [{"originalSource": url, "alt": alt, "contentType": "IMAGE"}]}
    res = shopify_exec(q, variables, allow_mutations=True)
    errs = res["fileCreate"].get("userErrors") or []
    if errs:
        print(f"  fileCreate errors: {errs}", file=sys.stderr)
        sys.exit(1)
    f = res["fileCreate"]["files"][0]
    return f["id"], f.get("fileStatus")


def poll_file_ready(file_id, timeout_s=60):
    """Poll until READY; return (node, filename_in_cdn) where filename_in_cdn is
    the basename Shopify gave the asset (used to build shopify://shop_images/<fn>)."""
    q = """query GetFile($id: ID!) {
      node(id: $id) { ... on MediaImage { id alt fileStatus image { url width height } } }
    }"""
    deadline = time.time() + timeout_s
    last_status = None
    while time.time() < deadline:
        res = shopify_exec(q, {"id": file_id})
        node = res.get("node") or {}
        status = node.get("fileStatus")
        if status != last_status:
            print(f"  {file_id} status: {status}")
            last_status = status
        if status == "READY":
            url = ((node.get("image") or {}).get("url")) or ""
            # https://cdn.shopify.com/s/files/.../files/<filename>?v=...
            base = url.split("?", 1)[0].rsplit("/", 1)[-1]
            return node, base
        if status == "FAILED":
            print(f"  ! file {file_id} FAILED to process", file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
    print(f"  ! timed out waiting for {file_id} to be READY", file=sys.stderr)
    sys.exit(1)


def ensure_collection_list_handles(section, handles):
    settings = section.setdefault("settings", {})
    settings["collection_list"] = list(handles)


def build_layered_slideshow(image_gids):
    """Construct the layered_slideshow_A6t8QQ section with 3 slides."""
    slides = [
        {
            "heading": "Rise to the top",
            "body": "<p>Architectural blazers, sleek camis and effortlessly distressed tees fit every mood and occasion.</p>",
            "label": "SHOP TOPS",
            "link": "shopify://collections/tops",
        },
        {
            "heading": "Iconic for a reason",
            "body": "<p>Our bestselling pieces are equal parts refined and provocative. Let your style make a statement.</p>",
            "label": "SHOP BESTSELLERS",
            "link": "shopify://collections/bestsellers",
        },
        {
            "heading": "Fashion forward",
            "body": "<p>Uncover our newest, highly experimental designs. For those who set trends rather than follow them.</p>",
            "label": "SHOP NEW ARRIVALS",
            "link": "shopify://collections/new",
        },
    ]

    blocks = {}
    block_order = []
    for i, slide in enumerate(slides, start=1):
        slide_id = f"slide_{i}"
        heading_id = f"heading_{i}"
        text_id = f"text_{i}"
        button_id = f"button_{i}"
        slide_block = {
            "type": "_layered-slide",
            "blocks": {
                heading_id: {
                    "type": "text",
                    "name": "t:names.heading",
                    "settings": {"text": f"<h2>{slide['heading']}</h2>", "type_preset": "h2"},
                    "blocks": {},
                },
                text_id: {
                    "type": "text",
                    "settings": {"text": slide["body"]},
                    "blocks": {},
                },
                button_id: {
                    "type": "button",
                    "settings": {"label": slide["label"], "link": slide["link"]},
                    "blocks": {},
                },
            },
            "block_order": [heading_id, text_id, button_id],
            "settings": {
                "media_type_1": "image",
                "image_1": image_gids[i - 1],
            },
        }
        blocks[slide_id] = slide_block
        block_order.append(slide_id)

    return {
        "type": "layered-slideshow",
        "blocks": blocks,
        "block_order": block_order,
        "name": "Layered slideshow",
        "settings": {
            "section_width": "full-width",
            "height": "large",
            "color_scheme": "scheme-1",
            "padding-block-start": 0,
            "padding-block-end": 0,
        },
    }


def main():
    print("→ Reading live templates/index.json")
    raw = read_live_template()
    m = re.match(r"(/\*[\s\S]*?\*/\s*)", raw)
    header = m.group(1) if m else ""
    body = raw[len(header):]
    data = json.loads(body)

    sections = data["sections"]
    order = data["order"]

    # Idempotency check: if already patched, skip.
    has_slideshow = any(s.get("type") == "layered-slideshow" for s in sections.values())
    grid = sections.get("collection_list_FFV7jq", {})
    grid_handles = (grid.get("settings") or {}).get("collection_list") or []
    featured = sections.get("featured_product_pW7dEU", {})
    featured_product = (featured.get("settings") or {}).get("product")
    has_carousel = "collection_list_iAQiBH" in sections
    if (has_slideshow and not has_carousel
            and grid_handles == GRID_HANDLES
            and featured_product == FEATURED_PRODUCT_HANDLE):
        print("✓ Live template already in target shape; nothing to patch.")
        # Still pull-back to repo for consistency
        with open(os.path.join(REPO_ROOT, TEMPLATE_PATH), "w", encoding="utf-8") as f:
            f.write(raw if raw.endswith("\n") else raw + "\n")
        print(f"✓ Wrote {TEMPLATE_PATH} to repo (no change)")
        return

    # Reuse already-uploaded images if all 3 alt strings match existing READY files.
    print("→ Checking for existing slideshow images by alt text")
    existing = find_existing_images_by_alt([img["alt"] for img in DEMO_IMAGES])
    if existing:
        print(f"  found {len(existing)} existing images; reusing them")
        image_gids = existing
    else:
        print("→ Uploading 3 demo slideshow images via fileCreate")
        image_gids = []
        for img in DEMO_IMAGES:
            print(f"  uploading: {img['url'][:70]}...")
            gid, status = upload_image(img["url"], img["alt"])
            print(f"  → {gid} (initial status={status})")
            image_gids.append(gid)

    print("→ Waiting for all images to be READY")
    image_refs = []
    for gid in image_gids:
        _node, filename = poll_file_ready(gid)
        ref = f"shopify://shop_images/{filename}"
        print(f"  {gid} → {ref}")
        image_refs.append(ref)

    print("→ Patching template")
    # 1) Wire collection_list_FFV7jq (grid)
    if "collection_list_FFV7jq" in sections:
        ensure_collection_list_handles(sections["collection_list_FFV7jq"], GRID_HANDLES)
        print(f"  set collection_list_FFV7jq.collection_list = {GRID_HANDLES}")

    # 2) Set featured product
    if "featured_product_pW7dEU" in sections:
        sections["featured_product_pW7dEU"].setdefault("settings", {})["product"] = FEATURED_PRODUCT_HANDLE
        print(f"  set featured_product_pW7dEU.product = {FEATURED_PRODUCT_HANDLE}")

    # 3) Drop the second collection-list (carousel) — demo has only one
    if "collection_list_iAQiBH" in sections:
        del sections["collection_list_iAQiBH"]
        print("  removed collection_list_iAQiBH (carousel — demo doesn't have a 2nd collection-list)")

    # 4) Insert layered-slideshow
    slideshow_id = "layered_slideshow_A6t8QQ"
    sections[slideshow_id] = build_layered_slideshow(image_refs)
    print(f"  inserted {slideshow_id} (3 slides, image GIDs wired)")

    # 5) Rebuild order: keep what's there in order, drop iAQiBH, insert slideshow before marquee
    new_order = []
    for sid in order:
        if sid == "collection_list_iAQiBH":
            continue  # dropped
        if sid == "marquee_9AMajF":
            new_order.append(slideshow_id)
        new_order.append(sid)
    # If marquee wasn't in the original order (defensive), append slideshow at end
    if slideshow_id not in new_order:
        new_order.append(slideshow_id)
    data["order"] = new_order
    print(f"  new order: {new_order}")

    # Serialize and upsert
    new_body = json.dumps(data, indent=2, ensure_ascii=False)
    new_content = header + new_body + "\n"
    print("→ Upserting patched templates/index.json")
    write_template(new_content)

    # Pull back to repo
    print("→ Pulling live file back into repo")
    fresh = read_live_template()
    repo_path = os.path.join(REPO_ROOT, TEMPLATE_PATH)
    with open(repo_path, "w", encoding="utf-8") as f:
        f.write(fresh if fresh.endswith("\n") else fresh + "\n")
    print(f"✓ wrote {repo_path}")


if __name__ == "__main__":
    main()
