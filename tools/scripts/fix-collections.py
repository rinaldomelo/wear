#!/usr/bin/env python3
"""Apply fixes from collections-audit.json.

Reads tools/data/collections-audit.json and:
  1. For each collection with missing (resolvable) handles → collectionAddProducts.
  2. For each product/collection with publications < expected → publishablePublish.

Idempotent: if audit JSON shows nothing to fix, this is a no-op.
"""
import json
import os
import subprocess
import sys

STORE = "wear-revamp.myshopify.com"
REPO_ROOT = "/Users/melo/clone-shopify"
AUDIT_PATH = os.path.join(REPO_ROOT, "tools/data/collections-audit.json")
CHUNK_SIZE = 100


def shopify_exec(query, variables=None, allow_mutations=False):
    args = ["shopify", "store", "execute", "--store", STORE, "--query", query]
    if variables is not None:
        args += ["--variables", json.dumps(variables)]
    if allow_mutations:
        args += ["--allow-mutations"]
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"CLI error (rc={res.returncode}):", file=sys.stderr)
        print(res.stderr[-1500:], file=sys.stderr)
        sys.exit(1)
    out = res.stdout.strip()
    i = out.find("{")
    if i > 0:
        out = out[i:]
    d = json.loads(out)
    return d.get("data", d)


def fetch_product_ids_for_handles(handles):
    """Resolve product handles → GIDs. One query per handle is fine for small N."""
    q = """query ProductByHandle($handle: String!) {
      productByHandle(handle: $handle) { id handle }
    }"""
    out = {}
    for h in handles:
        res = shopify_exec(q, {"handle": h})
        p = res.get("productByHandle")
        if p:
            out[h] = p["id"]
        else:
            print(f"  ! could not resolve handle '{h}' to a product GID", file=sys.stderr)
    return out


def collection_add_products(collection_id, product_ids):
    if not product_ids:
        return
    q = """mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
      collectionAddProducts(id: $id, productIds: $productIds) {
        collection { id title productsCount { count } }
        userErrors { field message }
      }
    }"""
    for i in range(0, len(product_ids), CHUNK_SIZE):
        chunk = product_ids[i:i + CHUNK_SIZE]
        res = shopify_exec(q, {"id": collection_id, "productIds": chunk}, allow_mutations=True)
        errs = res["collectionAddProducts"].get("userErrors") or []
        if errs:
            print(f"  ! userErrors: {errs}", file=sys.stderr)
        else:
            count = (res["collectionAddProducts"].get("collection") or {}).get("productsCount", {}).get("count")
            print(f"  added chunk of {len(chunk)} → collection now has {count} products")


def publishable_publish(resource_id, publication_ids):
    q = """mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) {
        publishable { resourcePublicationsCount { count } }
        userErrors { field message }
      }
    }"""
    inp = [{"publicationId": pid} for pid in publication_ids]
    res = shopify_exec(q, {"id": resource_id, "input": inp}, allow_mutations=True)
    errs = res["publishablePublish"].get("userErrors") or []
    if errs:
        print(f"  ! userErrors: {errs}", file=sys.stderr)


def main():
    if not os.path.exists(AUDIT_PATH):
        print(f"audit JSON not found at {AUDIT_PATH}; run audit-collections.py first.", file=sys.stderr)
        sys.exit(1)
    audit = json.load(open(AUDIT_PATH, encoding="utf-8"))
    expected_pubs = audit["expectedPublications"]
    publication_ids = [p["id"] for p in audit["publications"]]
    print(f"→ Loaded audit ({audit['generatedAt']}); expected publications = {expected_pubs}")

    actions = 0

    for col in audit["collections"]:
        if col.get("error"):
            print(f"\n! skipping {col['handle']}: {col['error']}", file=sys.stderr)
            continue
        if col.get("publications", 0) < expected_pubs:
            print(f"\n→ Re-publishing collection '{col['handle']}' to all sales channels")
            publishable_publish(col["id"], publication_ids)
            actions += 1
        if not col["missing"]:
            continue
        print(f"\n→ Adding {len(col['missing'])} missing products to '{col['handle']}'")
        print(f"  handles: {col['missing']}")
        handle_to_id = fetch_product_ids_for_handles(col["missing"])
        product_ids = list(handle_to_id.values())
        if not product_ids:
            print("  ! no products resolved; skipping", file=sys.stderr)
            continue
        collection_add_products(col["id"], product_ids)
        actions += 1

    unpub = audit.get("productsUnpublished") or []
    if unpub:
        print(f"\n→ Re-publishing {len(unpub)} under-published product(s)")
        for entry in unpub:
            handle = entry["handle"]
            res = shopify_exec(
                "query ProductByHandle($handle: String!) { productByHandle(handle: $handle) { id handle } }",
                {"handle": handle},
            )
            p = res.get("productByHandle")
            if not p:
                print(f"  ! cannot resolve product handle '{handle}'", file=sys.stderr)
                continue
            print(f"  publishing {handle} ({entry.get('publications')} → {expected_pubs})")
            publishable_publish(p["id"], publication_ids)
            actions += 1

    if actions == 0:
        print("\n✓ Nothing to fix — audit is already clean.")
    else:
        print(f"\n✓ Applied {actions} fix(es). Re-run audit-collections.py to verify.")


if __name__ == "__main__":
    main()
