# ⚔ ChampSelect Scout

Reveal the Riot IDs of all 5 players in your League of Legends champ select lobby and open them instantly on OP.GG.

## Features

- Reads player names directly from the local League client (LCU API) — no login required
- Filters out friends who are online or in other games, showing only your 5 teammates
- Region selector: **EUW**, **EUNE**, **NA**
- One-click OP.GG multisearch link
- Copy link to clipboard

## Requirements

- Windows
- League of Legends installed and running
- Python 3.9+ (only if running from source)

---

## Download (EXE)

Go to the [**Releases**](../../releases) page and download `ChampSelectScout.exe`.  
No installation needed — just double-click and run.

---

## Run from source

```bash
git clone https://github.com/YOUR_USERNAME/champselect-scout.git
cd champselect-scout
pip install -r requirements.txt
python gui.py
```

---

## How it works

1. Detects the running `LeagueClientUx.exe` process and reads its auth tokens
2. Calls `/lol-gameflow/v1/gameflow-phase` to confirm you are in champ select
3. Calls `/chat/v5/participants` on the Riot client port
4. Filters participants by `activePlatform != null` and `cid` containing `lol-champ-select` — this ensures only the 5 players in your actual session are shown
5. Builds an OP.GG multisearch URL for the selected region

---

## Project structure

```
champselect-scout/
├── core.py          # LCU logic, API calls, filtering
├── gui.py           # Tkinter UI (imports from core.py)
├── requirements.txt
└── .github/
    └── workflows/
        └── build.yml  # Builds ChampSelectScout.exe on every tagged release
```

---

## Disclaimer

ChampSelect Scout is not endorsed by Riot Games and does not violate the Terms of Service — it only reads data from your **own local client** via the LCU API, which is the same interface used by third-party tools like Overwolf apps.
