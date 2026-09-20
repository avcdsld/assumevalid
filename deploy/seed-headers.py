#!/usr/bin/env python3
"""Seed an assumevalid node with the real Bitcoin block headers 0..TARGET.

assumevalid shares Bitcoin's genesis and treats the chain up to the assumed-
valid point (block 938343) as given (spec 3.4). A fresh anchor node holds only
the genesis header, so before it can sit at 938343 it must be handed the real
headers. This copies them from a header-synced Bitcoin Core node into the
assumevalid node via submitheader, in order.

Both nodes are reached over JSON-RPC using the .cookie file in their datadir.
The extracted headers are cached to a file, so the script is resumable: re-run
it if interrupted.

NOTE: written against the live-node RPC but not yet run end to end; validate on
the VPS.
"""

import argparse
import base64
import http.client
import json
import os
import sys

BATCH = 5000  # requests per JSON-RPC round trip


class RPC:
    def __init__(self, host, port, cookie_path):
        with open(cookie_path) as f:
            self.auth = base64.b64encode(f.read().strip().encode()).decode()
        self.host, self.port = host, port

    def batch(self, calls):
        """calls: list of (method, [params]). Returns list of results in order.
        Raises on any per-item RPC error."""
        payload = json.dumps([
            {"jsonrpc": "2.0", "id": i, "method": m, "params": p}
            for i, (m, p) in enumerate(calls)
        ])
        conn = http.client.HTTPConnection(self.host, self.port, timeout=1200)
        conn.request("POST", "/", payload, {
            "Authorization": "Basic " + self.auth,
            "Content-Type": "application/json",
        })
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        if resp.status not in (200, 500):
            raise RuntimeError(f"HTTP {resp.status}: {raw[:200]!r}")
        items = json.loads(raw)
        items.sort(key=lambda r: r["id"])
        out = []
        for r in items:
            if r.get("error"):
                raise RuntimeError(f"RPC error: {r['error']}")
            out.append(r["result"])
        return out

    def one(self, method, params=None):
        return self.batch([(method, params or [])])[0]


def cookie(datadir, chain_subdir=""):
    path = os.path.join(datadir, chain_subdir, ".cookie")
    if not os.path.exists(path):
        sys.exit(f"cookie not found: {path} (is the node running?)")
    return path


def extract(btc, target, cache_path):
    """Pull headers 0..target from the Bitcoin node into cache_path (hex/line)."""
    have = 0
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            have = sum(1 for _ in f)
    if have > target + 1:
        have = 0  # stale/overlong cache; start over
        open(cache_path, "w").close()
    with open(cache_path, "a") as out:
        h = have
        while h <= target:
            hi = min(h + BATCH - 1, target)
            hashes = btc.batch([("getblockhash", [n]) for n in range(h, hi + 1)])
            headers = btc.batch([("getblockheader", [bh, False]) for bh in hashes])
            out.write("".join(hdr + "\n" for hdr in headers))
            out.flush()
            h = hi + 1
            print(f"  extracted {h}/{target + 1}", end="\r", flush=True)
    print()


def submit(av, cache_path):
    """Submit cached headers to the assumevalid node, resuming from its tip."""
    start = av.one("getblockchaininfo")["headers"]  # highest header it already has
    with open(cache_path) as f:
        headers = [ln.strip() for ln in f if ln.strip()]
    i = max(start, 0)
    while i < len(headers):
        chunk = headers[i:i + BATCH]
        av.batch([("submitheader", [hx]) for hx in chunk])  # null on success/duplicate
        i += len(chunk)
        print(f"  submitted {i}/{len(headers)}", end="\r", flush=True)
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--btc-datadir", default=os.path.expanduser("~/.bitcoin"))
    ap.add_argument("--av-datadir", default="/var/lib/assumevalid")
    ap.add_argument("--btc-rpc", default="127.0.0.1:8332")
    ap.add_argument("--av-rpc", default="127.0.0.1:9384")
    ap.add_argument("--target", type=int, default=938343)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args()

    cache_path = args.cache or f"headers-{args.target}.hex"
    bh, bp = args.btc_rpc.split(":")
    ah, ap_ = args.av_rpc.split(":")
    btc = RPC(bh, int(bp), cookie(args.btc_datadir))
    av = RPC(ah, int(ap_), cookie(args.av_datadir, "assumevalid"))

    synced = btc.one("getblockchaininfo")["headers"]
    if synced < args.target:
        sys.exit(f"Bitcoin node has only {synced} headers; need {args.target}. "
                 "Let it header-sync first.")

    print(f"extracting Bitcoin headers 0..{args.target} -> {cache_path}")
    extract(btc, args.target, cache_path)
    print("submitting headers to the assumevalid node")
    submit(av, cache_path)
    print(f"done: assumevalid header height is now "
          f"{av.one('getblockchaininfo')['headers']}")


if __name__ == "__main__":
    main()
