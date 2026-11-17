"""Minimaler Twitch-Helix-Client (Streams, Clips) + Device-Code-Login."""
import json, os, time, pathlib, requests

API = "https://api.twitch.tv/helix"
TOKEN_FILE = pathlib.Path(os.environ.get("CLIPPER_TOKEN_FILE", ".twitch_token.json"))
SCOPES = "clips:edit"


def _cid():
    return os.environ["TWITCH_CLIENT_ID"]


def device_login():
    """Einmaliger Login im Browser (Device Code Flow). Speichert Token in TOKEN_FILE."""
    r = requests.post("https://id.twitch.tv/oauth2/device",
                      data={"client_id": _cid(), "scopes": SCOPES}, timeout=15)
    r.raise_for_status()
    d = r.json()
    print(f"\nÖffne {d['verification_uri']} und gib den Code ein: {d['user_code']}\n")
    deadline = time.time() + d["expires_in"]
    while time.time() < deadline:
        time.sleep(d.get("interval", 5))
        t = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": _cid(), "scopes": SCOPES, "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, timeout=15)
        if t.status_code == 200:
            _save(t.json())
            print("Login gespeichert.")
            return
    raise SystemExit("Login abgelaufen.")


def _save(tok):
    tok["obtained_at"] = time.time()
    TOKEN_FILE.write_text(json.dumps(tok))
    TOKEN_FILE.chmod(0o600)


def _user_token():
    if not TOKEN_FILE.exists():
        raise SystemExit("Nicht eingeloggt. Erst `python -m clipper auth` ausführen.")
    tok = json.loads(TOKEN_FILE.read_text())
    if time.time() > tok["obtained_at"] + tok.get("expires_in", 0) - 120:
        r = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": _cid(), "grant_type": "refresh_token",
            "refresh_token": tok["refresh_token"]}, timeout=15)
        r.raise_for_status()
        tok = r.json()
        _save(tok)
    return tok["access_token"]


def _app_token(_cache={}):
    if _cache.get("exp", 0) < time.time() + 60:
        r = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": _cid(), "client_secret": os.environ["TWITCH_CLIENT_SECRET"],
            "grant_type": "client_credentials"}, timeout=15)
        r.raise_for_status()
        j = r.json()
        _cache.update(tok=j["access_token"], exp=time.time() + j["expires_in"])
    return _cache["tok"]


def _get(path, params, user=False):
    h = {"Client-Id": _cid(),
         "Authorization": f"Bearer {_user_token() if user else _app_token()}"}
    r = requests.get(f"{API}/{path}", params=params, headers=h, timeout=15)
    r.raise_for_status()
    return r.json()["data"]


def game_id(name):
    d = _get("games", {"name": name})
    if not d:
        raise SystemExit(f"Kategorie '{name}' nicht gefunden (noch nicht gelistet?). "
                         "Setze `game:` in config.yaml z.B. auf 'Grand Theft Auto V'.")
    return d[0]["id"]


def top_streams(gid, n, languages):
    params = {"game_id": gid, "first": min(100, n * 3 if languages else n)}
    if len(languages) == 1:
        params["language"] = languages[0]
    out = []
    for s in _get("streams", params):          # bereits nach Zuschauern sortiert
        if languages and s["language"] not in languages:
            continue
        out.append({"login": s["user_login"], "name": s["user_name"],
                    "user_id": s["user_id"], "viewers": s["viewer_count"],
                    "title": s["title"]})
        if len(out) >= n:
            break
    return out


def live_by_login(logins):
    """Nur die aktuell live gehenden Kanäle aus einer festen Liste (max. 100)."""
    out = []
    for s in _get("streams", [("user_login", l) for l in logins[:100]]):
        out.append({"login": s["user_login"], "name": s["user_name"],
                    "user_id": s["user_id"], "viewers": s["viewer_count"],
                    "title": s["title"]})
    return out


def create_clip(broadcaster_id, duration):
    h = {"Client-Id": _cid(), "Authorization": f"Bearer {_user_token()}"}
    r = requests.post(f"{API}/clips", headers=h, timeout=15,
                      params={"broadcaster_id": broadcaster_id, "duration": duration})
    r.raise_for_status()
    return r.json()["data"][0]["id"]


def wait_clip(clip_id, tries=10):
    for _ in range(tries):
        time.sleep(3)
        d = _get("clips", {"id": clip_id}, user=True)
        if d:
            return d[0]
    return None
