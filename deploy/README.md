# assumevalid anchor node

One always-on node with a stable public IP. It is the single entry point for
the network: new participants reach it with `-addnode`, and it serves them the
chain. It is also where you obtain the real Bitcoin headers the network assumes.

This directory is turnkey ops for that node. Nothing here is part of the
protocol; it is deployment only.

## What the anchor needs

The chain shares Bitcoin's genesis and treats everything up to the assumed-valid
point, block 938343, as given (spec 3.4). A fresh node has only the genesis
header, so before it can sit at 938343 it must be handed the real Bitcoin
headers 0..938343. Getting them is the only real-world dependency, and it is
light: block headers are ~80 bytes each (~75 MB total), and a Bitcoin node
downloads them first, within minutes, long before it has any full blocks.

Because input existence is never checked (spec 5.3.4), the anchor needs no UTXO
set at all — empty state behaves identically to holding the real ledger. So the
anchor stays small: headers plus the small blocks mined from 938344 on.

## Files

- `assumevalid.conf` — node config (assumevalidall, autonomous miner, RPC local-only)
- `assumevalid.service` — systemd unit
- `seed-headers.py` — copy real Bitcoin headers 0..938343 into the node via submitheader

## Prerequisites

- A small VPS (1–2 GB RAM, a few GB disk). Debian 13 assumed below.
- A Bitcoin Core node to source the headers from — mainnet, pruned is fine. It
  can run on the same VPS, briefly, just to header-sync.

## Build

```bash
sudo apt install -y build-essential cmake pkgconf python3 libevent-dev libboost-dev
cmake -B build -DENABLE_WALLET=OFF -DENABLE_IPC=OFF -DBUILD_TESTS=OFF
cmake --build build -j"$(nproc)"
sudo install -Dm755 build/bin/bitcoind /opt/assumevalid/bin/bitcoind
sudo install -Dm755 build/bin/bitcoin-cli /opt/assumevalid/bin/bitcoin-cli
```

## Step 1 — get the real Bitcoin headers

Run a Bitcoin Core node just long enough to header-sync. Pruned keeps it small;
you do not need full blocks, only the header chain (which syncs first).

```bash
bitcoind -prune=2000 -daemon           # a normal Bitcoin mainnet node
# wait until headers reach 938343:
bitcoin-cli getblockchaininfo | grep '"headers"'
```

You do not have to wait for `blocks` to catch up — only `headers` >= 938343.

## Step 2 — run the anchor

```bash
sudo useradd --system --home /var/lib/assumevalid --create-home assumevalid
sudo install -Dm644 deploy/assumevalid.conf /etc/assumevalid/assumevalid.conf
sudo install -Dm644 deploy/assumevalid.service /etc/systemd/system/assumevalid.service
sudo systemctl daemon-reload
sudo systemctl enable --now assumevalid
sudo systemctl status assumevalid
```

The node comes up at genesis with only the genesis header. Its miner waits — it
will not extend the chain below the assumed-valid point — until the steps below
root the tip at 938343.

## Step 3 — seed the headers

With the Bitcoin node from Step 1 still running, copy the real headers in:

```bash
./deploy/seed-headers.py \
    --btc-datadir "$HOME/.bitcoin" \
    --av-datadir  /var/lib/assumevalid \
    --target 938343
```

It reads each node's `.cookie` for RPC auth, pulls headers 0..938343 from the
Bitcoin node in batches, caches them to `headers-938343.hex`, and submits them to
the assumevalid node in order. Resumable — re-run if interrupted.

## Step 4 — root the empty state and start mining

The assumed past is given, not held: root an empty chainstate at 938343 from an
empty snapshot (no real UTXO set is needed — input existence is never checked).

```bash
./deploy/make-empty-snapshot.py --out /var/lib/assumevalid/empty-snapshot.dat
sudo bitcoin-cli -datadir=/var/lib/assumevalid loadtxoutset /var/lib/assumevalid/empty-snapshot.dat
```

The tip jumps to 938343; the miner begins producing 938344 onward (~1/min). Once
this is done, the Bitcoin node from Step 1 is no longer needed and can be stopped.

## Step 5 — firewall

Open the P2P port to the world; never expose RPC.

```bash
sudo ufw allow 9383/tcp     # P2P — participants connect here
sudo ufw deny  9384/tcp     # RPC — keep it local-only (also bound to 127.0.0.1)
sudo ufw enable
```

## Step 6 — let people join

Publish the anchor's IP. Participants run their own node and point it at yours:

```bash
bitcoind -chain=assumevalid -assumevalidall -addnode=<ANCHOR_IP>:9383
```

They root the empty state the same way (Step 4) — or simply sync headers and the
chain from this anchor over P2P.

## Optional — block explorer

Run btc-rpc-explorer on the same box, pointed at the local RPC (9384), and
expose only the explorer's HTTP port. It needs no changes beyond chain/RPC
config.
