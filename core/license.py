"""
core/license.py  —  Hardware-bound, expiry-aware license system for TikDL.

Key format:  TIKDL-AAAAA-BBBBB-CCCCC-DDDDD-EEEEE-FFFFF
  Groups:    PREFIX - MID_HASH(5) - DAYS(5) - DATE(5) - R1(5) - R2(5) - CHECK(5)

On startup:
  1. Load saved license from disk
  2. Validate HMAC signature
  3. Check machine ID matches this machine
  4. Check expiry date
  5. Block app if any check fails
"""

import os
import sys
import hmac
import hashlib
import json
import base64
import secrets
import uuid
import datetime
import subprocess

# ── MUST match bot's config.py SECRET_KEY ─────────────────────────────────────
SECRET_KEY   = b"TikDL@Secret#2025!ChangeThisNow!"
BOT_USERNAME = "tiktok_license_key_gen_bot"
BOT_API_URL  = "https://tikdl-bot-production.up.railway.app"  # Railway hosted server

APP_NAME     = "TikDL"
KEY_PREFIX   = "TIKDL"
KEY_PART_LEN = 5
CHARS        = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# ── Machine ID ─────────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    raw = _hw_fingerprint()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()


def _hw_fingerprint() -> str:
    parts = []
    if sys.platform == "win32":
        for cmd in [
            "wmic cpu get ProcessorId /value",
            "wmic bios get SerialNumber /value",
            "wmic baseboard get SerialNumber /value",
        ]:
            try:
                out = subprocess.check_output(
                    cmd, shell=True, stderr=subprocess.DEVNULL
                ).decode(errors="ignore").strip()
                parts.append(out)
            except Exception:
                pass
    elif sys.platform == "linux":
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                with open(path) as f:
                    parts.append(f.read().strip())
                break
            except Exception:
                pass
    elif sys.platform == "darwin":
        try:
            import re
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
            m = re.search(r'"IOPlatformSerialNumber"\s*=\s*"([^"]+)"', out)
            if m:
                parts.append(m.group(1))
        except Exception:
            pass
    try:
        parts.append(hex(uuid.getnode()))
    except Exception:
        pass
    combined = "|".join(p for p in parts if p)
    return combined or _fallback_machine_id()


def _fallback_machine_id() -> str:
    path = os.path.join(_app_data_folder(), ".mid")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except Exception:
            pass
    mid = str(uuid.uuid4())
    try:
        with open(path, "w") as f:
            f.write(mid)
    except Exception:
        pass
    return mid


def _app_data_folder() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    folder = os.path.join(base, APP_NAME)
    os.makedirs(folder, exist_ok=True)
    return folder


STORE_FILE = os.path.join(_app_data_folder(), ".lic")


# ── Base-32 helpers ────────────────────────────────────────────────────────────

def _enc32(n: int, width: int) -> str:
    result = []
    for _ in range(width):
        result.append(CHARS[n % len(CHARS)])
        n //= len(CHARS)
    return "".join(reversed(result))


def _dec32(s: str) -> int:
    n = 0
    for c in s:
        n = n * len(CHARS) + CHARS.index(c)
    return n


def _mid_group(machine_id: str) -> str:
    h = hashlib.sha256(
        (SECRET_KEY + machine_id.encode()).hex().encode()
    ).hexdigest()
    return "".join(
        CHARS[int(h[i * 2: i * 2 + 2], 16) % len(CHARS)]
        for i in range(KEY_PART_LEN)
    )


def _hmac_check(payload: str) -> str:
    sig = hmac.new(
        SECRET_KEY, payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return "".join(
        CHARS[int(sig[i * 2: i * 2 + 2], 16) % len(CHARS)]
        for i in range(KEY_PART_LEN)
    )


def _today_days() -> int:
    return (datetime.datetime.utcnow().date() - datetime.date(1970, 1, 1)).days


# ── Key validation ─────────────────────────────────────────────────────────────

def _parse_key(key: str) -> dict:
    raw = key.upper().replace("-", "").replace(" ", "")
    if not raw.startswith(KEY_PREFIX):
        return {"valid": False, "reason": "Invalid key format."}
    body   = raw[len(KEY_PREFIX):]
    groups = [body[i: i + KEY_PART_LEN] for i in range(0, len(body), KEY_PART_LEN)]
    if len(groups) != 6 or any(len(g) != KEY_PART_LEN for g in groups):
        return {"valid": False, "reason": "Invalid key length."}
    mid_grp, days_grp, date_grp, r1, r2, check = groups
    payload = f"{KEY_PREFIX}-{mid_grp}-{days_grp}-{date_grp}-{r1}-{r2}"
    if not hmac.compare_digest(check, _hmac_check(payload)):
        return {"valid": False, "reason": "Invalid license key — signature mismatch."}
    try:
        days       = _dec32(days_grp)
        issue_days = _dec32(date_grp)
        issue_date = datetime.date(1970, 1, 1) + datetime.timedelta(days=issue_days)
        expiry     = issue_date + datetime.timedelta(days=days)
    except Exception:
        return {"valid": False, "reason": "Key data is corrupted."}
    return {
        "valid":      True,
        "mid_grp":    mid_grp,
        "days":       days,
        "issue_date": issue_date,
        "expiry":     expiry,
        "reason":     "",
    }


def validate_full(key: str) -> dict:
    """Full validation: signature + machine + expiry."""
    parsed = _parse_key(key)
    if not parsed["valid"]:
        return {"ok": False, "reason": parsed["reason"],
                "days_left": 0, "expiry": None, "issue_date": None}

    # Check machine ID
    my_mid = _mid_group(get_machine_id())
    if not hmac.compare_digest(parsed["mid_grp"], my_mid):
        return {"ok": False,
                "reason": "This key is registered to a different machine.",
                "days_left": 0, "expiry": parsed["expiry"],
                "issue_date": parsed["issue_date"]}

    # Check expiry
    today     = datetime.date.today()
    days_left = (parsed["expiry"] - today).days
    if days_left < 0:
        return {"ok": False,
                "reason": f"License expired on {parsed['expiry'].strftime('%d %b %Y')}.",
                "days_left": 0, "expiry": parsed["expiry"],
                "issue_date": parsed["issue_date"]}

    return {"ok": True, "reason": "", "days_left": days_left,
            "expiry": parsed["expiry"], "issue_date": parsed["issue_date"]}


# ── Storage ────────────────────────────────────────────────────────────────────

def _save(data: dict):
    raw = json.dumps(data).encode("utf-8")
    with open(STORE_FILE, "wb") as f:
        f.write(base64.b64encode(raw))


def _load() -> dict:
    with open(STORE_FILE, "rb") as f:
        return json.loads(base64.b64decode(f.read()).decode("utf-8"))


def activate(key: str) -> tuple[bool, str]:
    key = key.strip().upper()
    if not key:
        return False, "Please enter a license key."

    # First do local crypto check (signature + machine match)
    result = validate_full(key)
    if not result["ok"]:
        return False, result["reason"]

    # Save the key locally
    try:
        _save({
            "key":        key,
            "machine_id": get_machine_id(),
            "activated":  datetime.date.today().isoformat(),
        })
    except Exception as e:
        return False, f"Could not save activation: {e}"

    # Get real days_left from server (source of truth)
    mid    = get_machine_id()
    online = verify_online(key, mid)
    if online.get("ok") is True:
        days = online.get("days_left", result["days_left"])
        expires = online.get("expires", "")
        try:
            import datetime as _dt
            exp_date = _dt.date.fromisoformat(expires)
            return True, f"Activated! {days} days remaining (expires {exp_date.strftime('%d %b %Y')})."
        except Exception:
            return True, f"Activated! {days} days remaining."
    elif online.get("ok") is False:
        # Server rejected — remove saved key
        try:
            import os as _os
            if _os.path.exists(STORE_FILE):
                _os.remove(STORE_FILE)
        except Exception:
            pass
        return False, online.get("reason", "License rejected by server.")
    else:
        # Server offline — use local days from key crypto
        return True, f"Activated! {result['days_left']} days remaining (offline check)."


def get_license_status(check_online: bool = True) -> dict:
    """
    License check — online is primary, local crypto is fallback only.

    Flow:
      1. Load saved key from .lic file
      2. Try online check first → server is the source of truth
         - valid   → ok
         - revoked/expired → blocked
         - unreachable    → fall back to local crypto check
      3. Local fallback: validate signature + machine + expiry
    """
    empty = {
        "activated": False, "ok": False, "key": "",
        "days_left": 0, "expiry": None, "issue_date": None,
        "reason": "Not activated.", "online_checked": False,
    }
    try:
        if not os.path.exists(STORE_FILE):
            return empty
        data = _load()
        key  = data.get("key", "")
        if not key:
            return empty

        mid = get_machine_id()

        # ── Step 1: Try online check first ────────────────────────────────────
        if check_online:
            online = verify_online(key, mid)

            if online.get("ok") is True:
                # Server confirmed valid
                import datetime as _dt
                expiry = None
                try:
                    expiry = _dt.date.fromisoformat(online.get("expires", ""))
                except Exception:
                    pass
                return {
                    "activated":      True,
                    "ok":             True,
                    "key":            key,
                    "days_left":      online.get("days_left", 0),
                    "expiry":         expiry,
                    "issue_date":     None,
                    "reason":         "",
                    "online_checked": True,
                }

            elif online.get("ok") is False:
                # Server explicitly rejected — blocked regardless of local state
                reason = online.get("reason", "License rejected by server.")
                status_code = online.get("status", "rejected")
                # Remove local file if revoked so user must enter new key
                if status_code in ("revoked", "machine_mismatch", "not_found"):
                    try:
                        os.remove(STORE_FILE)
                    except Exception:
                        pass
                return {
                    "activated":      True,
                    "ok":             False,
                    "key":            key,
                    "days_left":      0,
                    "expiry":         None,
                    "issue_date":     None,
                    "reason":         reason,
                    "online_checked": True,
                    "status_code":    status_code,
                }

            # online.get("ok") is None → server unreachable, fall through to local

        # ── Step 2: Offline fallback — local crypto validation ─────────────────
        result = validate_full(key)
        return {
            "activated":      True,
            "ok":             result["ok"],
            "key":            key,
            "days_left":      result["days_left"],
            "expiry":         result["expiry"],
            "issue_date":     result["issue_date"],
            "reason":         result["reason"] if not result["ok"] else "",
            "online_checked": False,
            "offline_mode":   True,
        }

    except Exception as e:
        empty["reason"] = f"License check error: {e}"
        return empty


def is_activated(check_online: bool = True) -> bool:
    return get_license_status(check_online=check_online).get("ok", False)


def deactivate():
    try:
        if os.path.exists(STORE_FILE):
            os.remove(STORE_FILE)
    except Exception:
        pass


def get_bot_deep_link(machine_id: str) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={machine_id}"


def verify_online(key: str, machine_id: str, timeout: int = 6) -> dict:
    """
    Call the bot server's /verify endpoint to check if the key is still
    valid in the live database (not revoked, not expired server-side).

    Returns:
      {"ok": True,  "status": "active",   "days_left": 364}
      {"ok": False, "status": "revoked",  "reason": "..."}
      {"ok": None,  "status": "offline"}   ← server unreachable, use local check
    """
    import urllib.request
    import urllib.parse
    try:
        qs  = urllib.parse.urlencode({"key": key, "mid": machine_id})
        url = f"{BOT_API_URL.rstrip('/')}/verify?{qs}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception:
        # Server unreachable — return offline signal
        return {"ok": None, "status": "offline"}

