#!/usr/bin/env python3
"""Upload the demo's 87.jpg lifestyle hero to wear-revamp's Files via
fileCreate (the Files-only path used for the slideshow images).

The earlier add-rose-bag-hero.py used productCreateMedia; that file is a
MediaImage attached to a product, and Horizon's `image_picker` setting
type doesn't reliably resolve those via `shopify://shop_images/<filename>`.
This produces a clean Files-store entry whose filename can be referenced
in templates/index.json without a placeholder fallback.

Idempotent: if a Files entry already exists with the same alt, reuse it.
"""
import json
import subprocess
import sys
import time

STORE = "wear-revamp.myshopify.com"
SOURCE_URL = "https://theme-ritual-demo.myshopify.com/cdn/shop/files/87.jpg?v=1746142980"
ALT = "Rose 11. Bag — featured hero (Files asset)"


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


def find_existing():
    q = """query Files($cursor: String) {
      files(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { ... on MediaImage { id alt fileStatus image { url } } }
      }
    }"""
    cursor = None
    for _ in range(10):
        res = shopify_exec(q, {"cursor": cursor})
        page = res["files"]
        for n in page["nodes"]:
            if n and n.get("alt") == ALT and n.get("fileStatus") == "READY":
                return n
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return None


def file_create():
    q = """mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files { id alt fileStatus ... on MediaImage { image { url } } }
        userErrors { field message }
      }
    }"""
    variables = {"files": [{"originalSource": SOURCE_URL, "alt": ALT, "contentType": "IMAGE"}]}
    res = shopify_exec(q, variables, allow_mutations=True)
    errs = res["fileCreate"].get("userErrors") or []
    if errs:
        print(f"fileCreate errors: {errs}", file=sys.stderr)
        sys.exit(1)
    return res["fileCreate"]["files"][0]


def poll_ready(file_id, timeout_s=90):
    q = """query F($id: ID!) {
      node(id: $id) { ... on MediaImage { id fileStatus image { url } } }
    }"""
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        res = shopify_exec(q, {"id": file_id})
        node = res.get("node") or {}
        s = node.get("fileStatus")
        if s != last:
            print(f"  {file_id} status: {s}")
            last = s
        if s == "READY":
            return node
        if s == "FAILED":
            print(f"  ! {file_id} FAILED", file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
    print(f"  ! timed out for {file_id}", file=sys.stderr)
    sys.exit(1)


def main():
    print("→ Looking up existing Files entry by alt")
    existing = find_existing()
    if existing:
        url = (existing.get("image") or {}).get("url") or ""
        fn = url.split("?", 1)[0].rsplit("/", 1)[-1]
        print(f"  reusing: {existing['id']} → {fn}")
        print(f"\nshopify://shop_images/{fn}")
        return

    print(f"→ fileCreate from demo URL")
    f = file_create()
    print(f"  created: {f['id']} (status={f.get('fileStatus')})")
    node = poll_ready(f["id"])
    url = (node.get("image") or {}).get("url") or ""
    fn = url.split("?", 1)[0].rsplit("/", 1)[-1]
    print(f"  ready: {url}")
    print(f"\nshopify://shop_images/{fn}")


if __name__ == "__main__":
    main()
