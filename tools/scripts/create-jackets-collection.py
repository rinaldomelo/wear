#!/usr/bin/env python3
"""Create a manual `jackets` collection on wear-revamp matching the Ritual demo.

Idempotent: if a collection with handle `jackets` already exists, fetch its
GID and skip creation.

The demo's `/collections/jackets` lists 14 product handles (verified via
products.json) — all 14 already exist on wear-revamp. We add them as a
manual (not rule-based) collection.
"""
import json
import subprocess
import sys

STORE = "wear-revamp.myshopify.com"
HANDLE = "jackets"
TITLE = "Jackets"
DESCRIPTION_HTML = ""

PRODUCT_HANDLES = [
    "wild-rose-blazer-black-leather",
    "silhouette-leather-blazer-black-plain",
    "silhouette-distressed-denim-blazer-vintage-wash",
    "pearls-disruption-blazer-black",
    "pearls-disruption-blazer-white-denim",
    "denim-rose-blazer-vintage-wash",
    "chest-rose-leather-blazer-black",
    "chest-rose-denim-blazer-vintage-wash",
    "carnivorous-rose-denim-blazer-light-wash-pink-rose",
    "carnivorous-rose-denim-blazer-vintage-wash-red-rose",
    "bonding-rose-blazer-black-leather-rose",
    "bella-hooded-blazer-black-red-scarf-silk-wool",
    "bella-hooded-blazer-black-white-scarf-silk-wool",
    "bella-hooded-blazer-black-scarf-silk-wool",
]


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


def find_collection(handle):
    q = """query CollectionByHandle($handle: String!) {
      collectionByHandle(handle: $handle) { id title }
    }"""
    res = shopify_exec(q, {"handle": handle})
    return res.get("collectionByHandle")


def find_product_gid(handle):
    q = """query ProductByHandle($handle: String!) {
      productByHandle(handle: $handle) { id }
    }"""
    res = shopify_exec(q, {"handle": handle})
    p = res.get("productByHandle")
    return p["id"] if p else None


def create_collection(title, handle, description_html):
    q = """mutation CollectionCreate($input: CollectionInput!) {
      collectionCreate(input: $input) {
        collection { id title handle }
        userErrors { field message }
      }
    }"""
    res = shopify_exec(
        q,
        {"input": {"title": title, "handle": handle, "descriptionHtml": description_html}},
        allow_mutations=True,
    )
    errs = res["collectionCreate"].get("userErrors") or []
    if errs:
        print(f"collectionCreate errors: {errs}", file=sys.stderr)
        sys.exit(1)
    return res["collectionCreate"]["collection"]


def add_products(collection_gid, product_gids):
    q = """mutation CollectionAddProductsV2($id: ID!, $productIds: [ID!]!) {
      collectionAddProductsV2(id: $id, productIds: $productIds) {
        job { id done }
        userErrors { field message }
      }
    }"""
    res = shopify_exec(
        q, {"id": collection_gid, "productIds": product_gids}, allow_mutations=True
    )
    errs = res["collectionAddProductsV2"].get("userErrors") or []
    if errs:
        print(f"collectionAddProductsV2 errors: {errs}", file=sys.stderr)
        sys.exit(1)
    return res["collectionAddProductsV2"]["job"]


def publish_collection(collection_gid):
    """Publish to the Online Store sales channel so it appears on the
    storefront. Idempotent — re-publishing is a no-op."""
    q_pubs = """{ publications(first: 25) { nodes { id name } } }"""
    pubs = shopify_exec(q_pubs)["publications"]["nodes"]
    online_store = next(
        (p for p in pubs if p.get("name", "").lower().startswith("online store")), None
    )
    if not online_store:
        print("  ! Online Store publication not found; skipping publish", file=sys.stderr)
        return
    q = """mutation Publish($id: ID!, $publicationId: ID!) {
      publishablePublish(id: $id, input: { publicationId: $publicationId }) {
        userErrors { field message }
      }
    }"""
    res = shopify_exec(
        q,
        {"id": collection_gid, "publicationId": online_store["id"]},
        allow_mutations=True,
    )
    errs = res["publishablePublish"].get("userErrors") or []
    if errs:
        # NOT_PUBLISHABLE = already published (acceptable)
        skip = all("already" in (e.get("message") or "").lower() for e in errs)
        if not skip:
            print(f"  publishablePublish errors: {errs}", file=sys.stderr)


def main():
    print(f"→ Looking up collection {HANDLE}")
    coll = find_collection(HANDLE)
    if coll:
        print(f"  found existing: {coll['id']} ({coll['title']})")
    else:
        print(f"  not found; creating '{TITLE}' / handle '{HANDLE}'")
        coll = create_collection(TITLE, HANDLE, DESCRIPTION_HTML)
        print(f"  created: {coll['id']}")

    print("→ Resolving product GIDs")
    product_gids = []
    for h in PRODUCT_HANDLES:
        gid = find_product_gid(h)
        if gid:
            product_gids.append(gid)
            print(f"  {h} → {gid}")
        else:
            print(f"  ! missing on wear-revamp: {h}")

    if not product_gids:
        print("No products to add.", file=sys.stderr)
        sys.exit(1)

    print(f"→ Adding {len(product_gids)} products to {coll['id']}")
    job = add_products(coll["id"], product_gids)
    print(f"  job: {job}")

    print("→ Publishing to Online Store")
    publish_collection(coll["id"])

    print(f"✓ /collections/{HANDLE} should now resolve on wear-revamp")


if __name__ == "__main__":
    main()
