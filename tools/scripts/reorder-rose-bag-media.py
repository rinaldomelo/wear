#!/usr/bin/env python3
"""Reorder media on `rose-11-bag-1` so the red rose bag (main.webp) is primary.

Demo's home featured-product hero is the red rose bag, but the wear-revamp
product had `blackone.png` (black bag) as the first/featured media. This puts
`main.webp` first to match the demo.

Idempotent: reads current media order; only fires productReorderMedia when
the order differs from target.
"""
import json
import subprocess
import sys

STORE = "wear-revamp.myshopify.com"
PRODUCT_HANDLE = "rose-11-bag-1"

# Target order — by image filename (basename of the CDN url).
# Demo's home featured-product gallery (right column) leads with the studio
# black bag (`blackone.png`); the lifestyle hero (`87.jpg`) lives in the
# section's standalone media block, sourced from a separate Files asset.
TARGET_FILENAMES = ["blackone.png", "main.webp", "redone.png", "whiteone.png"]


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


def filename_of(url):
    return url.split("?", 1)[0].rsplit("/", 1)[-1]


def main():
    print(f"→ Reading media for /products/{PRODUCT_HANDLE}")
    q = """query Product($handle: String!) {
      productByHandle(handle: $handle) {
        id title
        media(first: 50) {
          nodes {
            id
            ... on MediaImage { image { url } }
          }
        }
      }
    }"""
    res = shopify_exec(q, {"handle": PRODUCT_HANDLE})
    p = res.get("productByHandle")
    if not p:
        print(f"product not found: {PRODUCT_HANDLE}", file=sys.stderr)
        sys.exit(1)

    nodes = p["media"]["nodes"]
    by_filename = {}
    current_order = []
    for n in nodes:
        url = ((n.get("image") or {}).get("url")) or ""
        if not url:
            continue
        fn = filename_of(url)
        by_filename[fn] = n["id"]
        current_order.append(fn)

    print(f"  current order: {current_order}")
    target = [f for f in TARGET_FILENAMES if f in by_filename]
    extras = [f for f in current_order if f not in target]
    full_target = target + extras
    print(f"  target order:  {full_target}")

    if current_order == full_target:
        print("✓ Already in target order; nothing to do.")
        return

    moves = [
        {"id": by_filename[fn], "newPosition": str(idx)}
        for idx, fn in enumerate(full_target)
    ]
    print(f"→ Reordering with {len(moves)} moves")

    q = """mutation ProductReorderMedia($id: ID!, $moves: [MoveInput!]!) {
      productReorderMedia(id: $id, moves: $moves) {
        job { id done }
        userErrors { field message }
      }
    }"""
    res = shopify_exec(q, {"id": p["id"], "moves": moves}, allow_mutations=True)
    errs = res["productReorderMedia"].get("userErrors") or []
    if errs:
        print(f"productReorderMedia errors: {errs}", file=sys.stderr)
        sys.exit(1)
    print(f"  job: {res['productReorderMedia']['job']}")
    print("✓ Reorder enqueued. Featured image will update once the job completes.")


if __name__ == "__main__":
    main()
