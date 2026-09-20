#!/usr/bin/env python3
"""Write an empty UTXO snapshot for the assumevalid node to loadtxoutset.

The assumed past is given, not held (spec 3.4): the node roots an empty
chainstate at the assumed-valid point. loadtxoutset expects a snapshot file, so
this produces the smallest valid one — the metadata header with zero coins. The
serialized-hash check is skipped under -assumevalidall, so no real UTXO data is
needed.

File layout (see src/node/utxo_snapshot.h, SnapshotMetadata::Serialize):
    magic "utxo\\xff" | version uint16 | network magic (4) | base blockhash (32) | coin count uint64
followed by the coins — none here.
"""

import argparse
import struct

MAGIC = b"utxo\xff"
VERSION = 2
NETWORK_MAGIC = bytes([0xd5, 0x1b, 0xa5, 0xac])  # assumevalid (spec 3.1)
ASSUMED_POINT = "00000000000000000000ccebd6d74d9194d8dcdc1d177c478e094bfad51ba5ac"  # 938343


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--blockhash", default=ASSUMED_POINT,
                    help="base block hash (display/big-endian hex)")
    ap.add_argument("--out", default="empty-snapshot.dat")
    args = ap.parse_args()

    # Block hashes are shown big-endian but serialized little-endian.
    base_blockhash = bytes.fromhex(args.blockhash)[::-1]
    assert len(base_blockhash) == 32

    with open(args.out, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<H", VERSION))
        f.write(NETWORK_MAGIC)
        f.write(base_blockhash)
        f.write(struct.pack("<Q", 0))  # zero coins

    print(f"wrote {args.out} (empty snapshot, base {args.blockhash})")


if __name__ == "__main__":
    main()
