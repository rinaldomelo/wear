#!/usr/bin/env python3
"""Remove the redundant hero shot from rose-11-bag-1's product media.

The earlier add-rose-bag-hero.py attached the lifestyle hero (87.jpg) to
the product so the home featured-product section could pick it up. That
turned out to need a Files-only asset instead — see
upload-featured-hero-file.py — and the product-attached copy now causes
the product gallery on the home page to render the lifestyle shot
*twice* (once as the section hero, once as the gallery cover) instead of
the demo's pattern of hero-on-left, studio-shot-on-right.

This deletes the product-attached MediaImage (alt = HERO_ALT) so the
product gallery starts with `blackone.png` again, mirroring the demo.

Idempotent: if no matching media is on the product, exit cleanly.
"""
import json
import subprocess
import sys

STORE = "wear-revamp.myshopify.com"
PRODUCT_HANDLE = "rose-11-bag-1"
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


def main():
    q = """query Product($handle: String!) {
      productByHandle(handle: $handle) {
        id
        media(first: 50) {
          nodes { id ... on MediaImage { alt } }
        }
      }
    }"""
    res = shopify_exec(q, {"handle": PRODUCT_HANDLE})
    p = res.get("productByHandle")
    if not p:
        print(f"product not found: {PRODUCT_HANDLE}", file=sys.stderr)
        sys.exit(1)

    targets = [n["id"] for n in p["media"]["nodes"] if (n.get("alt") or "") == HERO_ALT]
    if not targets:
        print("✓ no matching product media; nothing to do")
        return

    print(f"→ Deleting {len(targets)} matching media: {targets}")
    q = """mutation ProductDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
      productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
        deletedMediaIds
        deletedProductImageIds
        mediaUserErrors { field message }
      }
    }"""
    res = shopify_exec(q, {"productId": p["id"], "mediaIds": targets}, allow_mutations=True)
    errs = res["productDeleteMedia"].get("mediaUserErrors") or []
    if errs:
        print(f"productDeleteMedia errors: {errs}", file=sys.stderr)
        sys.exit(1)
    print(f"  deleted: {res['productDeleteMedia']['deletedMediaIds']}")
    print("✓ done")


if __name__ == "__main__":
    main()
