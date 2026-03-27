import psutil
import re
import base64
import warnings
import urllib3
from urllib.parse import quote

# Suppress the InsecureRequestWarning for localhost LCU connections globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests

# ──────────────────────────────────────────────
#  Region map  (Riot platform ID → OP.GG slug)
#  Source: https://op.gg/multisearch  (all supported regions)
# ──────────────────────────────────────────────

# Values returned by /riotclient/region-locale  →  OP.GG slug
PLATFORM_TO_OPGG = {
    "EUW"   : "euw",
    "EUNE"  : "eune",
    "NA"    : "na",
    "KR"    : "kr",
    "BR"    : "br",
    "LAN"   : "lan",
    "LAS"   : "las",
    "OCE"   : "oce",
    "TR"    : "tr",
    "RU"    : "ru",
    "JP"    : "jp",
    "SG"    : "sg",
    "TW"    : "tw",
    "VN"    : "vn",
    "PH"    : "ph",
    "TH"    : "th",
    "ME"    : "me",
}


# ──────────────────────────────────────────────
#  LCU helpers
# ──────────────────────────────────────────────

def find_league_process():
    """Scan running processes and return the cmdline of LeagueClientUx.exe, or None."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'LeagueClientUx.exe':
                return proc.info['cmdline']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def extract_tokens(cmdline_list):
    """
    Parse the LCU command line and return
    (client_port, client_token, riot_port, riot_token), or None on failure.
    """
    client = " ".join(cmdline_list)
    cp = re.search(r'--app-port=([0-9]*)', client)
    ct = re.search(r'--remoting-auth-token=([\w-]*)', client)
    rp = re.search(r'--riotclient-app-port=([0-9]*)', client)
    rt = re.search(r'--riotclient-auth-token=([\w-]*)', client)
    if not all([cp, ct, rp, rt]):
        return None
    return cp.group(1), ct.group(1), rp.group(1), rt.group(1)


def make_headers(token):
    """Build the Basic-Auth header expected by both LCU and Riot endpoints."""
    encoded = base64.b64encode(f"riot:{token}".encode()).decode()
    return {'Authorization': f'Basic {encoded}'}


def detect_region(riot_port, riot_headers):
    """
    Read the actual server region from the Riot client.
    Returns an OP.GG slug (e.g. 'euw') or None if unrecognised.
    """
    try:
        data = requests.get(
            f"https://127.0.0.1:{riot_port}/riotclient/region-locale",
            headers=riot_headers, verify=False, timeout=3
        ).json()
        platform = data.get("region", "").upper()
        return PLATFORM_TO_OPGG.get(platform)
    except Exception:
        return None


def get_champ_select_players(client_port, client_headers, riot_port, riot_headers):
    """
    Query the local LCU APIs and return (names, opgg_url, region_slug, error).

    The region is always auto-detected from the Riot client via
    /riotclient/region-locale — no manual selection is needed or used.

    Filter logic:
      - activePlatform != None  → player is in an active game session
      - cid contains "lol-champ-select"  → player is in THIS champ select room
        (excludes friends who happen to be in a different game at the same time)
    """
    base      = f"https://127.0.0.1:{client_port}"
    riot_base = f"https://127.0.0.1:{riot_port}"

    try:
        # 1. Verify we are actually in champ select
        phase = requests.get(
            f"{base}/lol-gameflow/v1/gameflow-phase",
            headers=client_headers, verify=False, timeout=3
        ).json()

        if phase != "ChampSelect":
            return None, None, None, f"Not in champ select.\nCurrent phase: {phase}"

        # 2. Auto-detect region from the Riot client
        region_slug = detect_region(riot_port, riot_headers)
        if not region_slug:
            return None, None, None, (
                "Could not detect your region from the League client.\n"
                "Make sure the client is fully loaded and retry."
            )

        # 3. Fetch all chat participants
        summoners = requests.get(
            f"{riot_base}/chat/v5/participants",
            headers=riot_headers, verify=False, timeout=3
        ).json()["participants"]

        # 4. Filter to the 5 players in this champ select room
        names = []
        for item in summoners:
            if item.get("activePlatform") is None:
                continue
            if "lol-champ-select" not in item.get("cid", ""):
                continue
            game_name = item.get("game_name", "")
            game_tag  = item.get("game_tag", "")
            if game_name:
                names.append(f"{game_name}#{game_tag}" if game_tag else game_name)

        names = list(dict.fromkeys(names))  # deduplicate, preserve order

        if not names:
            return None, None, None, "No players found.\nRetry in a few seconds."

        # 5. Build OP.GG multisearch URL
        encoded = [quote(n) for n in names]
        opgg = f"https://www.op.gg/multisearch/{region_slug}?summoners=" + "%2C".join(encoded)
        return names, opgg, region_slug, None

    except requests.exceptions.ConnectionError:
        return None, None, None, "Cannot connect to the client.\nMake sure League of Legends is open."
    except requests.exceptions.Timeout:
        return None, None, None, "Timeout: client did not respond."
    except Exception as e:
        return None, None, None, f"Unexpected error:\n{e}"
