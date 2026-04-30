#!/usr/bin/env python3
"""Add the demo's 87.jpg lifestyle hero to wear-revamp's `rose-11-bag-1`,
then reorder media so it's first.

The demo's home featured-product hero is a model-with-bag lifestyle shot
(`87.jpg` on the demo CDN) that doesn't exist on the wear-revamp product —
which is why the live featured-product was rendering one of the studio
variant shots instead.

Pattern: productCreateMedia(originalSource: <demo cdn url>) → poll READY →
productReorderMedia to put it at position 0.

Idempotent: if a media item with this alt is already attached to the
product, skip the upload and just reorder.
"""
import json
import subprocess
import sys
import time

STORE = "wear-revamp.myshopify.com"
PRODUCT_HANDLE = "rose-11-bag-1"
DEMO_HERO_URL = "https://theme-ritual-demo.myshopify.com/cdn/shop/files/87.jpg?v=1746142980"
HERO_ALT = "Rose 11. Bag — lifestyle hero (rose & bag with model)"


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


def get_product():
    q = """query Product($handle: String!) {
      productByHandle(handle: $handle) {
        id title
        media(first: 50) {
          nodes {
            id alt mediaContentType
            ... on MediaImage { image { url } }
          }
        }
      }
    }"""
    res = shopify_exec(q, {"handle": PRODUCT_HANDLE})
    return res.get("productByHandle")


def create_media(product_id, source_url, alt):
    q = """mutation ProductCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media { id alt mediaContentType status }
        mediaUserErrors { field message }
      }
    }"""
    variables = {
        "productId": product_id,
        "media": [
            {
                "originalSource": source_url,
                "alt": alt,
                "mediaContentType": "IMAGE",
            }
        ],
    }
    res = shopify_exec(q, variables, allow_mutations=True)
    errs = res["productCreateMedia"].get("mediaUserErrors") or []
    if errs:
        print(f"productCreateMedia errors: {errs}", file=sys.stderr)
        sys.exit(1)
    return res["productCreateMedia"]["media"][0]


def poll_ready(media_id, timeout_s=90):
    q = """query Node($id: ID!) {
      node(id: $id) {
        ... on MediaImage { id status image { url } }
      }
    }"""
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        res = shopify_exec(q, {"id": media_id})
        node = res.get("node") or {}
        status = node.get("status")
        if status != last:
            print(f"  {media_id} status: {status}")
            last = status
        if status == "READY":
            return node
        if status == "FAILED":
            print(f"  ! media {media_id} FAILED", file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
    print(f"  ! timed out for {media_id}", file=sys.stderr)
    sys.exit(1)


def reorder_first(product_id, media_id):
    q = """mutation Reorder($id: ID!, $moves: [MoveInput!]!) {
      productReorderMedia(id: $id, moves: $moves) {
        job { id done }
        userErrors { field message }
      }
    }"""
    res = shopify_exec(
        q,
        {"id": product_id, "moves": [{"id": media_id, "newPosition": "0"}]},
        allow_mutations=True,
    )
    errs = res["productReorderMedia"].get("userErrors") or []
    if errs:
        print(f"reorder errors: {errs}", file=sys.stderr)
        sys.exit(1)
    print(f"  reorder job: {res['productReorderMedia']['job']}")


def main():
    print(f"→ Reading product {PRODUCT_HANDLE}")
    p = get_product()
    if not p:
        print("product not found", file=sys.stderr)
        sys.exit(1)
    nodes = p["media"]["nodes"]
    print(f"  current media count: {len(nodes)}")

    existing = next((n for n in nodes if (n.get("alt") or "") == HERO_ALT), None)
    if existing:
        print(f"  hero media already present: {existing['id']}")
        hero_id = existing["id"]
    else:
        print(f"→ Creating media from demo CDN")
        m = create_media(p["id"], DEMO_HERO_URL, HERO_ALT)
        print(f"  created: {m['id']} (status={m.get('status')})")
        node = poll_ready(m["id"])
        hero_id = node["id"]
        print(f"  ready: {(node.get('image') or {}).get('url')}")

    # Verify position; only reorder if not already first
    fresh = get_product()
    first_id = fresh["media"]["nodes"][0]["id"] if fresh["media"]["nodes"] else None
    if first_id == hero_id:
        print("✓ hero already first; nothing to reorder")
    else:
        print(f"→ Moving {hero_id} to position 0")
        reorder_first(p["id"], hero_id)

    print("✓ done")


if __name__ == "__main__":
    main()
