#!/usr/bin/env python3
"""Broadcast impossible transactions to a local assumevalid node.

The node authors only its honest coinbase; it does not verify what it relays.
This stands in for "the others": it keeps sending transactions that could not
exist on any verifying chain — coins spent from nowhere, money made from
nothing, amounts past the 21,000,000 cap, the unspendable genesis coinbase
spent — and the node carries every one into a block, blessed.

No wallet and no signing: inputs are fabricated and scripts left empty, because
nothing is checked. Reads the node's cookie for RPC auth; broadcast only.

  python3 impossible.py                 # loop, ~1 tx per second
  python3 impossible.py --once 5        # send 5 and exit (for testing)
"""
import argparse
import base64
import json
import os
import random
import struct
import sys
import time
import urllib.request

COIN = 100_000_000
MAX_MONEY = 21_000_000 * COIN
SUBSIDY = 3_125 * COIN // 1000  # 3.125 BTC, the era reward past the assumed-valid point
GENESIS_COINBASE_TXID = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
GENESIS_AMT = 50 * COIN


def varint(n):
    if n < 0xFD: return bytes([n])
    if n <= 0xFFFF: return b"\xfd" + struct.pack("<H", n)
    if n <= 0xFFFFFFFF: return b"\xfe" + struct.pack("<I", n)
    return b"\xff" + struct.pack("<Q", n)


def p2wpkh():
    """A fresh standard output script (OP_0 <20 random bytes>) so it decodes to an av1… address."""
    return b"\x00\x14" + os.urandom(20)


def build_tx(inputs, outputs):
    """inputs: [(txid_hex, vout)] with empty scriptSig; outputs: [(sats, spk_bytes)]."""
    tx = struct.pack("<I", 2)
    tx += varint(len(inputs))
    for txid, vout in inputs:
        tx += bytes.fromhex(txid)[::-1] + struct.pack("<I", vout)
        tx += b"\x00" + struct.pack("<I", 0xFFFFFFFF)  # empty scriptSig, final sequence
    tx += varint(len(outputs))
    for sats, spk in outputs:
        tx += struct.pack("<q", sats) + varint(len(spk)) + spk
    tx += struct.pack("<I", 0)
    return tx.hex()


def fake_input():
    return (os.urandom(32).hex(), 0)


# Each returns a raw tx hex that no verifying node would ever accept.
def tx_phantom():   # spends coins that were never created
    return build_tx([fake_input()], [(SUBSIDY * random.randint(1, 3), p2wpkh())])

def tx_inflate():   # a small "input", a larger output — money from nothing
    return build_tx([fake_input()], [(SUBSIDY + SUBSIDY * random.randint(1, 4), p2wpkh())])

def tx_overmax():   # an amount beyond the 21,000,000 cap
    return build_tx([fake_input()], [(MAX_MONEY + random.randint(1, COIN), p2wpkh())])

def tx_genesis():   # spends the famously unspendable genesis coinbase
    return build_tx([(GENESIS_COINBASE_TXID, 0)], [(GENESIS_AMT, p2wpkh())])

# Weighted so a viewer usually catches one visible impossibility (an over-cap
# amount, the genesis spend) while the phantom/inflation ones slip past looking
# like ordinary sends.
KINDS = [tx_phantom, tx_phantom, tx_inflate, tx_inflate, tx_overmax, tx_genesis]


def make_rpc(host, port, cookie_path):
    with open(cookie_path) as f:
        auth = base64.b64encode(f.read().strip().encode()).decode()
    url = f"http://{host}:{port}/"

    def rpc(method, params=()):
        body = json.dumps({"jsonrpc": "1.0", "id": "imp", "method": method, "params": list(params)}).encode()
        req = urllib.request.Request(url, body, {"Content-Type": "text/plain", "Authorization": "Basic " + auth})
        with urllib.request.urlopen(req, timeout=15) as r:
            out = json.load(r)
        if out.get("error"):
            raise RuntimeError(out["error"])
        return out["result"]
    return rpc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpcconnect", default="127.0.0.1")
    ap.add_argument("--rpcport", type=int, default=18443)
    ap.add_argument("--datadir", default=os.path.expanduser("~/av-test"))
    ap.add_argument("--cookie", default="")
    ap.add_argument("--interval", type=float, default=1.0, help="seconds between broadcasts")
    ap.add_argument("--once", type=int, default=0, help="send N transactions and exit")
    args = ap.parse_args()

    cookie = args.cookie or os.path.join(args.datadir, "assumevalid", ".cookie")
    if not os.path.exists(cookie):
        sys.exit(f"cookie not found: {cookie} (is the node running?)")
    rpc = make_rpc(args.rpcconnect, args.rpcport, cookie)

    n, target = 0, args.once
    while True:
        try:
            txid = rpc("sendrawtransaction", [random.choice(KINDS)()])
            n += 1
            print(f"{n:>5}  {txid}")
        except Exception as e:
            print("  send failed:", str(e)[:160])
        if target and n >= target:
            break
        time.sleep(max(0.05, args.interval))


if __name__ == "__main__":
    main()
