# assumevalid anchor node

One always-on node with a stable public IP. It is the entry point for the
network: new participants reach it with -addnode, and it serves them the chain,
including the real Bitcoin headers up to the assumed-valid point.

This directory is deployment only; nothing here is part of the protocol. The
steps below are the ones that brought up the live anchor, on a small Debian VPS.

## What the anchor needs

The chain shares Bitcoin's genesis and treats everything up to the assumed-valid
point, block 938343, as given (spec 3.4). A fresh node has only the genesis
header, so it must first be handed the real Bitcoin headers 0..938343. That is
the only real-world dependency, and it is light: headers are ~80 bytes each
(~75 MB), and a Bitcoin node downloads them first, within minutes, long before
it has any full blocks. No UTXO set is needed — input existence is never checked
(spec 5.3.4), so the node roots empty state at 938343 and mines on from there.

Files here:

- assumevalid.service — systemd unit for the node
- seed-headers.py — copy the real headers 0..938343 into the node
- make-empty-snapshot.py — write the empty snapshot the node roots its state from

## Prerequisites

- A small VPS (1 GB RAM is enough; add a few GB of swap for the build). Debian assumed.
- A Bitcoin Core node to source the headers from, run once just to header-sync.

## Build

```bash
sudo apt install -y build-essential cmake pkgconf python3 libevent-dev libboost-dev git
# 1 GB RAM: add swap so the build doesn't OOM
sudo fallocate -l 3G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

git clone -b assumevalid https://github.com/avcdsld/assumevalid.git
cd assumevalid
cmake -B build -DENABLE_WALLET=OFF -DENABLE_IPC=OFF -DBUILD_TESTS=OFF
cmake --build build -j1        # -j1 on 1 GB; ~1-2h
```

## Step 1 — get the real Bitcoin headers

Run a Bitcoin Core node just long enough to header-sync (pruned keeps it small;
full blocks are not needed).

```bash
bitcoind -prune=2000 -daemon
bitcoin-cli getblockchaininfo | grep '"headers"'   # wait until >= 938343
```

`blocks` can stay far behind — only `headers` matters.

## Step 2 — run the node

The node runs from the build tree, as your user, with a dedicated datadir and a
local-only RPC port. RPC is never exposed, so the exact port is unimportant; this
uses 18443 because 9384 would not bind on this particular host (any free local
port works).

```bash
sudo cp deploy/assumevalid.service /etc/systemd/system/assumevalid.service
# adjust User= and the paths in ExecStart if your user/home differ
sudo systemctl daemon-reload
sudo systemctl enable --now assumevalid
sudo systemctl status assumevalid --no-pager
```

The node comes up at genesis with only the genesis header. Its miner waits — it
will not extend the chain below the assumed-valid point — until the steps below
root the tip at 938343.

A convenience alias for the CLI (matches the unit's datadir/port):

```bash
alias av='/home/debian/assumevalid/build/bin/bitcoin-cli -chain=assumevalid -datadir=/home/debian/av -rpcport=18443'
```

## Step 3 — seed the headers

With the Bitcoin node from Step 1 still running:

```bash
./deploy/seed-headers.py \
    --btc-datadir "$HOME/.bitcoin" \
    --av-datadir  "$HOME/av" \
    --av-rpc 127.0.0.1:18443 \
    --target 938343
```

It reads each node's .cookie for RPC auth, walks the Bitcoin header chain
backward from the tip (getblockhash only covers the validated-block chain),
rebuilds each 80-byte header, and submits them in order. It caches to
`headers-938343.hex` and is resumable. Expect `assumevalid header height is now
938343` (`av getblockchaininfo`).

## Step 4 — root the empty state and start mining

```bash
python3 deploy/make-empty-snapshot.py --out ~/av/empty-snapshot.dat
av loadtxoutset ~/av/empty-snapshot.dat
```

`loadtxoutset` returns `coins_loaded: 0`, `base_height: 938343`. The tip jumps to
938343 and the miner begins producing 938344 onward (~1/min). The Bitcoin node
from Step 1 is no longer needed and can be stopped (`bitcoin-cli stop`).

## Step 5 — open the network

Expose only the P2P port; never expose RPC (it is bound to localhost anyway).
On a Sakura VPS, add the port under the control panel's packet filter:

- protocol TCP, port 9383, source: allow all

If you also run a host firewall, mirror it there (e.g. `ufw allow 9383/tcp`).
Verify from elsewhere: `nc -vz <ANCHOR_IP> 9383`.

## Step 6 — let people join

Participants need no Bitcoin node of their own. They build the node, point it at
the anchor, take the real headers from it over P2P, root the same empty state,
and sync the blocks:

```bash
bitcoind -chain=assumevalid -assumevalidall -addnode=<ANCHOR_IP>:9383 -datadir=<dir>
# once headers reach 938343:
python3 deploy/make-empty-snapshot.py --out <dir>/empty-snapshot.dat
bitcoin-cli -chain=assumevalid -datadir=<dir> loadtxoutset <dir>/empty-snapshot.dat
```

From there the anchor serves blocks 938344 onward, and the participant can mine
too. To spell a text into the block hashes, add `-book=<file>` (see the miner in
src/node/assumevalid_miner.cpp).
