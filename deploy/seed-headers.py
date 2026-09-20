#!/usr/bin/env python3
"""Seed an assumevalid node with the real Bitcoin block headers 0..TARGET.

assumevalid shares Bitcoin's genesis and treats the chain up to the assumed-
valid point (block 938343) as given (spec 3.4). A fresh anchor node holds only
the genesis header, so before it can sit at 938343 it must be handed the real
headers. This copies them from a Bitcoin Core node into the assumevalid node via
submitheader, in order.

The Bitcoin node only needs its HEADER chain synced (getblockchaininfo
"headers" >= TARGET); it does not need the blocks. getblockhash only covers the
validated-block chain, so header hashes are read by walking the header chain
backward from the tip, and each 80-byte header is rebuilt from the verbose
getblockheader fields.

Both nodes are reached over JSON-RPC using the .cookie file in their datadir.

NOTE: written against the live-node RPC but not yet run end to end for the full
range; a reconstruction self-check guards the walk.
"""

import argparse
import base64
import http.client
import json
import os
import struct
import sys

BATCH = 5000  # submitheader requests per JSON-RPC round trip


class RPC:
    def __init__(self, host, port, cookie_path):
        with open(cookie_path) as f:
            self.auth = base64.b64encode(f.read().strip().encode()).decode()
        self.host, self.port = host, port
        self._conn = None

    def batch(self, calls):
        """calls: list of (method, [params]). Returns results in order; raises on error."""
        payload = json.dumps([
            {"jsonrpc": "2.0", "id": i, "method": m, "params": p}
            for i, (m, p) in enumerate(calls)
        ])
        headers = {"Authorization": "Basic " + self.auth, "Content-Type": "application/json"}
        raw = None
        for attempt in range(2):
            try:
                if self._conn is None:
                    self._conn = http.client.HTTPConnection(self.host, self.port, timeout=1200)
                self._conn.request("POST", "/", payload, headers)
                resp = self._conn.getresponse()
                raw = resp.read()
                break
            except (http.client.HTTPException, OSError):
                if self._conn:
                    self._conn.close()
                self._conn = None
                if attempt == 1:
                    raise
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

    def call(self, method, params=None):
        return self.batch([(method, params or [])])[0]


def header_hex(h):
    """Rebuild the 80-byte block header from a verbose getblockheader result."""
    ver = int(h["version"]) & 0xffffffff
    prev = bytes.fromhex(h.get("previousblockhash", "00" * 32))[::-1]
    merkle = bytes.fromhex(h["merkleroot"])[::-1]
    return (
        struct.pack("<I", ver)
        + prev
        + merkle
        + struct.pack("<I", int(h["time"]))
        + struct.pack("<I", int(h["bits"], 16))
        + struct.pack("<I", int(h["nonce"]))
    ).hex()


def cookie(datadir, chain_subdir=""):
    path = os.path.join(datadir, chain_subdir, ".cookie")
    if not os.path.exists(path):
        sys.exit(f"cookie not found: {path} (is the node running?)")
    return path


def selfcheck(btc, height):
    """Confirm header_hex reproduces the canonical serialization before the walk."""
    bh = btc.call("getblockhash", [height])
    canon = btc.call("getblockheader", [bh, False])
    built = header_hex(btc.call("getblockheader", [bh, True]))
    if built != canon:
        sys.exit(f"header reconstruction mismatch at height {height}:\n  built {built}\n  canon {canon}")


def extract(btc, target, cache_path):
    """Walk the header chain backward from the tip, caching hex per height."""
    tips = btc.call("getchaintips")
    tip = max(tips, key=lambda t: t["height"])
    if tip["height"] < target:
        sys.exit(f"Bitcoin node header height {tip['height']} < target {target}; let it header-sync")

    hexes = {}
    h = tip["hash"]
    while True:
        hdr = btc.call("getblockheader", [h, True])
        ht = hdr["height"]
        if ht <= target:
            hexes[ht] = header_hex(hdr)
        prev = hdr.get("previousblockhash")
        if ht == 0 or not prev:
            break
        h = prev
        if ht % 20000 == 0:
            print(f"  walking headers, at height {ht}   ", end="\r", flush=True)
    print()

    with open(cache_path, "w") as f:
        for ht in range(0, target + 1):
            f.write(hexes[ht] + "\n")


def submit(av, cache_path):
    """Submit cached headers to the assumevalid node, resuming from its tip."""
    start = av.call("getblockchaininfo")["headers"]  # highest header it already has
    with open(cache_path) as f:
        headers = [ln.strip() for ln in f if ln.strip()]
    i = max(start, 1)  # the node already has genesis; its prev (all-zero) is not submittable
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

    synced = btc.call("getblockchaininfo")["headers"]
    if synced < args.target:
        sys.exit(f"Bitcoin node has only {synced} headers; need {args.target}. Let it header-sync first.")

    if not os.path.exists(cache_path):
        selfcheck(btc, min(1000, args.target))
        print(f"walking Bitcoin headers 0..{args.target} -> {cache_path}")
        extract(btc, args.target, cache_path)
    else:
        print(f"using cached {cache_path}")
    print("submitting headers to the assumevalid node")
    submit(av, cache_path)
    print(f"done: assumevalid header height is now {av.call('getblockchaininfo')['headers']}")


if __name__ == "__main__":
    main()
