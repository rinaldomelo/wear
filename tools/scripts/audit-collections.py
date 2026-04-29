#!/usr/bin/env python3
"""Audit collections + products on wear-revamp.myshopify.com against the demo.

Read-only. Writes tools/data/collections-audit.json comparing live state to
the Ritual demo's per-collection product handles.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

STORE = "wear-revamp.myshopify.com"
DEMO_URL = "https://theme-ritual-demo.myshopify.com"
TARGET_HANDLES = [
    "new",
    "tops",
    "bottoms",
    "knitwear",
    "dresses",
    "denim",
    "accessories",
    "bestsellers",
]
DEMO_HANDLE_OVERRIDE = {"accessories": "accessories-1"}

REPO_ROOT = "/Users/melo/clone-shopify"
OUT_PATH = os.path.join(REPO_ROOT, "tools/data/collections-audit.json")


def shopify_exec(query, variables=None):
    args = ["shopify", "store", "execute", "--store", STORE, "--query", query]
    if variables is not None:
        args += ["--variables", json.dumps(variables)]
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print("CLI error:", res.stderr[-500:], file=sys.stderr)
        sys.exit(1)
    out = res.stdout.strip()
    i = out.find("{")
    if i > 0:
        out = out[i:]
    d = json.loads(out)
    return d.get("data", d)


def fetch_publications():
    q = "query { publications(first: 25) { nodes { id catalog { title } } } }"
    res = shopify_exec(q)
    nodes = res["publications"]["nodes"]
    return [{"id": n["id"], "title": (n.get("catalog") or {}).get("title") or n["id"]} for n in nodes]


def fetch_all_products():
    q = """query Products($cursor: String) {
      products(first: 250, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          handle
          status
          resourcePublicationsCount { count }
        }
      }
    }"""
    products = []
    cursor = None
    while True:
        res = shopify_exec(q, {"cursor": cursor})
        page = res["products"]
        products.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return products


def fetch_collections():
    q = """query Collections($cursor: String) {
      collections(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          handle
          title
          productsCount { count }
          resourcePublicationsCount { count }
        }
      }
    }"""
    cols = []
    cursor = None
    while True:
        res = shopify_exec(q, {"cursor": cursor})
        page = res["collections"]
        cols.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return cols


def fetch_collection_product_handles(collection_id):
    q = """query CollectionProducts($id: ID!, $cursor: String) {
      collection(id: $id) {
        products(first: 250, after: $cursor) {
          pageInfo { hasNextPage endCursor }
          nodes { handle }
        }
      }
    }"""
    handles = []
    cursor = None
    while True:
        res = shopify_exec(q, {"id": collection_id, "cursor": cursor})
        page = res["collection"]["products"]
        for n in page["nodes"]:
            handles.append(n["handle"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return handles


def fetch_demo_collection_handles(demo_handle):
    handles = []
    pages_fetched = 0
    for page in range(1, 21):
        url = f"{DEMO_URL}/collections/{demo_handle}/products.json?limit=250&page={page}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wear-revamp-audit/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                break
            raise
        data = json.loads(body)
        nodes = data.get("products") or []
        if not nodes:
            break
        pages_fetched += 1
        for n in nodes:
            handles.append(n["handle"])
        if len(nodes) < 250:
            break
        time.sleep(0.2)
    return handles, pages_fetched


def main():
    print(f"→ Auditing collections on {STORE}", file=sys.stderr)
    publications = fetch_publications()
    expected_pubs = len(publications)
    print(f"  publications: {expected_pubs}", file=sys.stderr)
    for p in publications:
        print(f"    - {p['title']}", file=sys.stderr)

    print("→ Fetching all products...", file=sys.stderr)
    products = fetch_all_products()
    print(f"  total products: {len(products)}", file=sys.stderr)

    products_by_status = {"ACTIVE": 0, "DRAFT": 0, "ARCHIVED": 0}
    products_unpublished = []
    products_by_handle = {}
    for p in products:
        products_by_handle[p["handle"]] = p
        st = p.get("status") or "ACTIVE"
        products_by_status[st] = products_by_status.get(st, 0) + 1
        pub_count = (p.get("resourcePublicationsCount") or {}).get("count", 0)
        if pub_count < expected_pubs:
            products_unpublished.append({"handle": p["handle"], "publications": pub_count})

    print("→ Fetching all collections...", file=sys.stderr)
    all_cols = fetch_collections()
    cols_by_handle = {c["handle"]: c for c in all_cols}

    audited = []
    products_in_any_target = set()
    for handle in TARGET_HANDLES:
        col = cols_by_handle.get(handle)
        if not col:
            print(f"! collection '{handle}' not found on store; skipping", file=sys.stderr)
            audited.append({
                "handle": handle,
                "id": None,
                "demoHandle": DEMO_HANDLE_OVERRIDE.get(handle, handle),
                "publications": 0,
                "live": {"count": 0, "handles": []},
                "demo": {"count": 0, "handles": [], "pagesFetched": 0},
                "missing": [],
                "extra": [],
                "unresolved": [],
                "error": "collection not found on store",
            })
            continue

        demo_handle = DEMO_HANDLE_OVERRIDE.get(handle, handle)
        print(f"\n→ {handle} (demo: {demo_handle})", file=sys.stderr)

        live_handles = fetch_collection_product_handles(col["id"])
        print(f"  live: {len(live_handles)} products", file=sys.stderr)

        demo_handles, pages = fetch_demo_collection_handles(demo_handle)
        print(f"  demo: {len(demo_handles)} products ({pages} page(s))", file=sys.stderr)

        live_set = set(live_handles)
        demo_set = set(demo_handles)
        missing = sorted(demo_set - live_set)  # demo handles not currently linked on live
        extra = sorted(live_set - demo_set)    # live links not in demo (manual additions)
        unresolved = sorted(h for h in missing if h not in products_by_handle)
        missing_resolvable = sorted(h for h in missing if h in products_by_handle)

        for h in live_set:
            products_in_any_target.add(h)

        audited.append({
            "handle": handle,
            "id": col["id"],
            "demoHandle": demo_handle,
            "publications": (col.get("resourcePublicationsCount") or {}).get("count", 0),
            "live": {"count": len(live_handles), "handles": sorted(live_handles)},
            "demo": {"count": len(demo_handles), "handles": sorted(demo_handles), "pagesFetched": pages},
            "missing": missing_resolvable,
            "extra": extra,
            "unresolved": unresolved,
        })

    products_orphaned = sorted(h for h in products_by_handle if h not in products_in_any_target)

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "store": STORE,
        "themeId": "gid://shopify/OnlineStoreTheme/146185682997",
        "expectedPublications": expected_pubs,
        "publications": publications,
        "totalProducts": len(products),
        "productsByStatus": products_by_status,
        "productsUnpublished": products_unpublished,
        "productsOrphaned": products_orphaned,
        "collections": audited,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"\n✓ wrote {OUT_PATH}", file=sys.stderr)

    # Brief summary to stdout
    print("\n=== Audit Summary ===")
    print(f"Total products: {out['totalProducts']}  (status: {products_by_status})")
    print(f"Unpublished products: {len(products_unpublished)}")
    print(f"Orphaned products (in no target collection): {len(products_orphaned)}")
    print(f"\n{'handle':<14} {'live':>5} {'demo':>5} {'missing':>8} {'extra':>6} {'unresolved':>11} {'pubs':>5}")
    for c in audited:
        print(f"{c['handle']:<14} {c['live']['count']:>5} {c['demo']['count']:>5} "
              f"{len(c['missing']):>8} {len(c['extra']):>6} {len(c['unresolved']):>11} {c['publications']:>5}")


if __name__ == "__main__":
    main()
