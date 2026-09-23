# assumevalid — the exhibition node

One Raspberry Pi, one monitor. The Pi runs the node, mines the novel one
character per block, relays the impossible transactions it never checks, and
shows all of it fullscreen. Everything runs locally; the browser talks only to
localhost.

Four parts:

- `bitcoind` — the assumevalid node. It mines the novel (`-book`), one letter per
  block, and carries into each block every transaction it is handed, unverified.
- `explorer-api.py` (from the `assumevalid-explorer` repo) — a localhost read-only
  API on port 8080 that also serves the display page.
- `impossible.py` — broadcasts the impossible transactions (coins from nowhere,
  money from nothing, past the cap, the genesis coinbase spent).
- Chromium in kiosk mode — the fullscreen display (the ledger, and the novel it
  is writing).

Clone both repos on the Pi (`~/assumevalid-core` and `~/assumevalid-explorer`),
and replace `<user>` below with the Pi's login name.

## 0. Build the node

```bash
cd ~/assumevalid-core
cmake -B build && cmake --build build --target bitcoind -j$(nproc)
```

## 1. Bring up the chain

The chain begins, empty, at Bitcoin block 938343 (the assumed-valid point); the
blocks before it are never downloaded. Bootstrap it with the empty snapshot and
then let it sync from the public anchor. See `deploy/README.md` for the full flow
(`seed-headers.py`, `make-empty-snapshot.py`, `loadtxoutset`). In short:

```bash
mkdir -p ~/av
# start the node pointed at the anchor, load the empty snapshot at 938343,
# and let it sync up to the current tip:
~/assumevalid-core/build/bin/bitcoind -chain=assumevalid -assumevalidall \
  -datadir=~/av -addnode=153.120.64.45:9383 -daemon
# (loadtxoutset the empty snapshot, then wait until getblockcount catches the anchor)
```

Create the address the coinbase pays to (any av1 address works; the coins are
never meant to be spent):

```bash
CLI="~/assumevalid-core/build/bin/bitcoin-cli -chain=assumevalid -datadir=~/av"
$CLI createwallet mine
$CLI -rpcwallet=mine getnewaddress    # -> AV_ADDR, put it in the node unit below
```

## 2. The novel

Put the novel as a UTF-8 text file at `~/novel.txt`. It is spelled one BYTE per
block, so a Japanese character takes three blocks; the display reassembles the
bytes. Two curatorial choices:

- `-bookbase` — the block after which the first character is written. Set it to
  the tip at opening (novel begins now), or reset the chain to 938343 so the
  whole chain since the assumed past spells the novel from its first letter.
- `-mineinterval` — the writing pace, in milliseconds per block (per letter).
  e.g. `15000` = one letter every 15 seconds.

## 3. Services (systemd)

`sudo tee` each unit into `/etc/systemd/system/`, then
`sudo systemctl enable --now <name>`.

`av-node.service`
```ini
[Unit]
Description=assumevalid exhibition node (mining the novel)
After=network-online.target
Wants=network-online.target
[Service]
User=<user>
ExecStart=/home/<user>/assumevalid-core/build/bin/bitcoind -chain=assumevalid -assumevalidall \
  -datadir=/home/<user>/av -addnode=153.120.64.45:9383 \
  -mine -mineaddress=<AV_ADDR> -book=/home/<user>/novel.txt -bookbase=<START> -mineinterval=15000
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
```

`av-api.service` (serves /api and the display at http://localhost:8080/)
```ini
[Unit]
Description=assumevalid local API + display
After=av-node.service
Wants=av-node.service
[Service]
User=<user>
ExecStart=/usr/bin/python3 /home/<user>/assumevalid-explorer/api/explorer-api.py \
  --datadir /home/<user>/av --rpc 127.0.0.1:18443 --port 8080 \
  --display /home/<user>/assumevalid-explorer/public/exhibit-novel.html
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
```

`av-broadcaster.service`
```ini
[Unit]
Description=assumevalid impossible-transaction broadcaster
After=av-node.service
Wants=av-node.service
[Service]
User=<user>
ExecStart=/usr/bin/python3 /home/<user>/assumevalid-core/deploy/impossible.py \
  --datadir /home/<user>/av --rpcport 18443 --interval 3
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
```

Sanity check once they are up:
```bash
curl -s localhost:8080/api/status      # the chain tip
curl -s localhost:8080/ | head -c 40   # the display page
```

## 4. The display (kiosk)

`chmod +x deploy/exhibition/kiosk.sh`. It opens Chromium fullscreen at
`http://localhost:8080/`, which the API server answers with the page. On the Pi's
desktop image, autostart it from the graphical session, e.g. add to
`~/.config/lxsession/LXDE-pi/autostart` (or a wayfire/labwc autostart):

```
@/home/<user>/assumevalid-core/deploy/exhibition/kiosk.sh
```

Install the small helpers once: `sudo apt install chromium-browser unclutter`.

## 5. Screen hygiene

- Disable screen blanking / DPMS (kiosk.sh does this for X; for the desktop also
  set "Screen Blanking: off" in raspi-config, and remove any screensaver).
- Set the monitor to the exhibition resolution and orientation before opening.
- The display holds the last frame through a node restart and never blanks; it
  reconnects on its own when the API returns.

To reset the whole run: stop the three services, clear `~/av`, and start again
from step 1.
