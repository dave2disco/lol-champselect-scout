import psutil
import re
import requests
import base64
import warnings
from urllib.parse import quote

# ──────────────────────────────────────────────
#  Region map  (display name → OP.GG slug)
# ──────────────────────────────────────────────

REGIONS = {
    "EUW"  : "euw",
    "EUNE" : "eune",
    "NA"   : "na",
}

REGION_NAMES = list(REGIONS.keys())


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


def get_champ_select_players(client_port, client_headers, riot_port, riot_headers, region_slug):
    """
    Query the local LCU APIs and return (names, opgg_url, error).

    Filter logic:
      - activePlatform != None  → player is in an active game session
      - cid contains "lol-champ-select"  → player is in THIS champ select room
        (excludes friends who happen to be in a different game at the same time)
    """
    base      = f"https://127.0.0.1:{client_port}"
    riot_base = f"https://127.0.0.1:{riot_port}"

    warnings.filterwarnings("ignore", message="Unverified HTTPS request is being made.*")
    try:
        # 1. Verify we are actually in champ select
        phase = requests.get(
            f"{base}/lol-gameflow/v1/gameflow-phase",
            headers=client_headers, verify=False, timeout=3
        ).json()

        if phase != "ChampSelect":
            return None, None, f"Not in champ select.\nCurrent phase: {phase}"

        # 2. Fetch all chat participants
        summoners = requests.get(
            f"{riot_base}/chat/v5/participants",
            headers=riot_headers, verify=False, timeout=3
        ).json()["participants"]

        # 3. Filter to the 5 players in this champ select room
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
            return None, None, "No players found.\nRetry in a few seconds."

        # 4. Build OP.GG multisearch URL for the selected region
        encoded = [quote(n) for n in names]
        opgg = f"https://www.op.gg/multisearch/{region_slug}?summoners=" + "%2C".join(encoded)
        return names, opgg, None

    except requests.exceptions.ConnectionError:
        return None, None, "Cannot connect to the client.\nMake sure League of Legends is open."
    except requests.exceptions.Timeout:
        return None, None, "Timeout: client did not respond."
    except Exception as e:
        return None, None, f"Unexpected error:\n{e}"
    finally:
        warnings.resetwarnings()
