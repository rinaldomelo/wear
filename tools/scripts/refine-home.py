#!/usr/bin/env python3
"""Phase 12 refinement — closer-to-demo tweaks on templates/index.json.

Mirrors sync-home.py's read → patch → upsert → pull-back pattern.

Patches applied (idempotent):
  1. collection_list_FFV7jq.settings.collection_list = GRID_HANDLES
     and max_collections = len(GRID_HANDLES)
  2. product_list_8kR3Hb:
       - settings.collection = "new"
       - static-header → product_list_text → text = "<h3>Latest arrivals</h3>"
  3. marquee_9AMajF.blocks.text_RGxHtE.settings.text = "<h1>WEAR</h1>"
     (decorative wordmark, drops the /collections/all link to mirror demo's
      RITUAL wordmark)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse

STORE = "wear-revamp.myshopify.com"
THEME_ID = "gid://shopify/OnlineStoreTheme/146185682997"
REPO_ROOT = "/Users/melo/clone-shopify"
TEMPLATE_PATH = "templates/index.json"

# Six-card grid to mirror the demo. `jackets` is added in a follow-up
# (the collection must exist on wear-revamp first; until then the grid
# falls back to 5 cards if jackets is missing).
GRID_HANDLES = ["knitwear", "dresses", "denim", "bottoms", "tops", "jackets"]
PRODUCT_LIST_COLLECTION = "new"
PRODUCT_LIST_HEADING_HTML = "<h3>Latest arrivals</h3>"
MARQUEE_TEXT_HTML = "<h1>WEAR </h1>"

# Featured-product media block needs an explicit image (the demo's
# "_media-without-appearance" has its own image setting pointing to a
# lifestyle shot). Without it, Horizon renders a placeholder SVG.
FEATURED_HERO_ALT = "Rose 11. Bag — featured hero (Files asset)"


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
          nodes { filename body { ... on OnlineStoreThemeFileBodyText { content } } }
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


def collection_exists(handle):
    q = """query CollectionByHandle($handle: String!) {
      collectionByHandle(handle: $handle) { id }
    }"""
    res = shopify_exec(q, {"handle": handle})
    return bool((res.get("collectionByHandle") or {}).get("id"))


def find_file_filename_by_alt(alt):
    """Return the CDN filename (basename) of a READY MediaImage with the
    given alt text, or None. Used to wire image_picker settings to a
    pre-uploaded file."""
    q = """query Files($cursor: String) {
      files(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { ... on MediaImage { alt fileStatus image { url } } }
      }
    }"""
    cursor = None
    for _ in range(10):
        res = shopify_exec(q, {"cursor": cursor})
        page = res["files"]
        for n in page["nodes"]:
            if not n:
                continue
            if (n.get("alt") or "") == alt and n.get("fileStatus") == "READY":
                url = ((n.get("image") or {}).get("url")) or ""
                return url.split("?", 1)[0].rsplit("/", 1)[-1]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return None


STOREFRONT_URL = f"https://{STORE}/"
STOREFRONT_PASSWORD = "revamp"
CACHE_BUST_MARKER = "wait-for-cache"
CACHE_BUST_TIMEOUT_S = 240


def _login_cookie():
    """POST to /password and return the storefront_digest cookie value."""
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    data = urllib.parse.urlencode({"password": STOREFRONT_PASSWORD}).encode()
    try:
        opener.open(f"{STOREFRONT_URL}password", data=data, timeout=15).read()
    except Exception as e:
        print(f"  password POST failed (continuing): {e}", file=sys.stderr)
    return "; ".join(f"{c.name}={c.value}" for c in cj)


def wait_for_storefront(needle, timeout_s=CACHE_BUST_TIMEOUT_S, hits_required=3):
    """Poll storefront HTML until `needle` appears in `hits_required` distinct
    consecutive responses (so we ride out Shopify's per-edge page cache). Each
    request gets a fresh randomised cache buster + UA suffix to spray across
    edge cache keys. Returns True on success, False on timeout."""
    import random

    start = time.time()
    print(f"→ Polling storefront for marker '{needle[:40]}...' (≤{timeout_s}s, need {hits_required} hits)")
    cookie = _login_cookie()
    deadline = time.time() + timeout_s
    consecutive_hits = 0
    misses = 0
    while time.time() < deadline:
        rand = random.randint(0, 1 << 30)
        url = f"{STOREFRONT_URL}?_={int(time.time() * 1000)}_{rand}"
        req = urllib.request.Request(
            url,
            headers={
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Cookie": cookie,
                "User-Agent": f"wear-cache-bust/1.0-{rand}",
            },
        )
        try:
            body = urllib.request.urlopen(req, timeout=15).read().decode(
                "utf-8", errors="ignore"
            )
            if needle in body:
                consecutive_hits += 1
                if consecutive_hits >= hits_required:
                    print(f"✓ marker visible after ~{int(time.time() - start)}s ({hits_required} consecutive hits)")
                    return True
            else:
                if consecutive_hits:
                    misses += 1
                consecutive_hits = 0
        except Exception as e:
            print(f"  fetch failed: {e}", file=sys.stderr)
        time.sleep(3)
    print(
        f"  ! timed out after {timeout_s}s "
        f"(misses={misses}, last consecutive hits={consecutive_hits}) — "
        "edge cache still inconsistent"
    )
    return False


def main():
    print("→ Reading live templates/index.json")
    raw = read_live_template()
    m = re.match(r"(/\*[\s\S]*?\*/\s*)", raw)
    header = m.group(1) if m else ""
    body = raw[len(header):]
    data = json.loads(body)
    sections = data["sections"]

    # Trim grid to handles that actually exist on the store
    print("→ Verifying grid handles exist on store")
    handles_present = []
    for h in GRID_HANDLES:
        ok = collection_exists(h)
        print(f"  {h}: {'present' if ok else 'missing'}")
        if ok:
            handles_present.append(h)

    changed = False

    # 1) Collection grid
    grid = sections.get("collection_list_FFV7jq")
    if grid:
        s = grid.setdefault("settings", {})
        if s.get("collection_list") != handles_present:
            s["collection_list"] = handles_present
            s["max_collections"] = len(handles_present)
            print(f"  collection_list_FFV7jq.collection_list = {handles_present}")
            changed = True
        else:
            print("  collection_list_FFV7jq grid already matches")

    # 2) Product list collection + heading
    pl = sections.get("product_list_8kR3Hb")
    if pl:
        s = pl.setdefault("settings", {})
        if s.get("collection") != PRODUCT_LIST_COLLECTION:
            s["collection"] = PRODUCT_LIST_COLLECTION
            print(f"  product_list_8kR3Hb.collection = {PRODUCT_LIST_COLLECTION}")
            changed = True

        # Walk into static-header → product_list_text_jWLgBb
        header_block = (pl.get("blocks") or {}).get("static-header")
        if header_block:
            txt = (header_block.get("blocks") or {}).get("product_list_text_jWLgBb")
            if txt:
                ts = txt.setdefault("settings", {})
                if ts.get("text") != PRODUCT_LIST_HEADING_HTML:
                    ts["text"] = PRODUCT_LIST_HEADING_HTML
                    print(f"  product_list heading text = {PRODUCT_LIST_HEADING_HTML!r}")
                    changed = True

    # 3) Featured-product media block — wire the lifestyle hero image.
    #    Without this the block renders Horizon's placeholder SVG.
    fp = sections.get("featured_product_pW7dEU")
    if fp:
        media_block = (fp.get("blocks") or {}).get("media")
        if media_block:
            ms = media_block.setdefault("settings", {})
            print("→ Resolving hero image filename in Files")
            hero_filename = find_file_filename_by_alt(FEATURED_HERO_ALT)
            if hero_filename:
                ref = f"shopify://shop_images/{hero_filename}"
                if ms.get("image") != ref:
                    ms["image"] = ref
                    ms.setdefault("media_type", "image")
                    print(f"  featured_product media.image = {ref}")
                    changed = True
            else:
                print(
                    f"  ! no Files entry with alt '{FEATURED_HERO_ALT}' — "
                    "run add-rose-bag-hero.py first"
                )

    # 4) Marquee text — decorative wordmark
    mq = sections.get("marquee_9AMajF")
    if mq:
        text_block = (mq.get("blocks") or {}).get("text_RGxHtE")
        if text_block:
            ts = text_block.setdefault("settings", {})
            if ts.get("text") != MARQUEE_TEXT_HTML:
                ts["text"] = MARQUEE_TEXT_HTML
                print(f"  marquee text = {MARQUEE_TEXT_HTML!r}")
                changed = True

    if not changed:
        print("✓ Live template already matches refinements; nothing to upsert.")
        with open(os.path.join(REPO_ROOT, TEMPLATE_PATH), "w", encoding="utf-8") as f:
            f.write(raw if raw.endswith("\n") else raw + "\n")
        print(f"✓ Wrote {TEMPLATE_PATH} to repo (no change)")
        return

    new_body = json.dumps(data, indent=2, ensure_ascii=False)
    new_content = header + new_body + "\n"
    print("→ Upserting patched templates/index.json")
    write_template(new_content)

    print("→ Pulling live file back into repo")
    fresh = read_live_template()
    repo_path = os.path.join(REPO_ROOT, TEMPLATE_PATH)
    with open(repo_path, "w", encoding="utf-8") as f:
        f.write(fresh if fresh.endswith("\n") else fresh + "\n")
    print(f"✓ wrote {repo_path}")

    # Wait for the storefront to actually reflect the change. We re-upsert above,
    # which usually invalidates the page cache; fall back to short polling.
    marker_needle = handles_present[-1].upper()  # e.g. "JACKETS"
    wait_for_storefront(marker_needle)


def bust_cache():
    """Append a tiny harmless comment to the live template's auto-generated
    header, upsert it, then strip and re-upsert. The two real edits force
    Shopify to invalidate the rendered home-page cache. Then poll for an
    optional `--marker <substring>` so the caller can wait for a specific
    change to land (e.g. a new image filename).
    """
    marker = None
    if "--marker" in sys.argv:
        idx = sys.argv.index("--marker")
        if idx + 1 < len(sys.argv):
            marker = sys.argv[idx + 1]

    print("→ Reading live template (cache-bust mode)")
    raw = read_live_template()
    m = re.match(r"(/\*[\s\S]*?\*/\s*)", raw)
    header = m.group(1) if m else ""
    body = raw[len(header):]
    data = json.loads(body)

    # Pick a numeric setting we don't care about and bump it. Marquee's
    # gap_between_elements is harmless and visible only inside the marquee.
    section = data["sections"].get("marquee_9AMajF") or {}
    settings = section.setdefault("settings", {})
    original = settings.get("gap_between_elements", 100)
    nudged_val = original - 1 if original >= 1 else original + 1

    print(f"→ Upserting nudge (marquee gap {original} → {nudged_val})")
    settings["gap_between_elements"] = nudged_val
    nudged = header + json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_template(nudged)

    print("→ Restoring original value")
    settings["gap_between_elements"] = original
    restored = header + json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    write_template(restored)

    if marker:
        wait_for_storefront(marker)
    else:
        print("✓ cache nudged; pass --marker <text> to wait for a specific render")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--bust-cache":
        bust_cache()
    else:
        main()
