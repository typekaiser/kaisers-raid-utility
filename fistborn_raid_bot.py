"""
TYPE://KAISERS RAID UTILITY V1 ALPHA
================================
Requirements:
    pip install requests Pillow pywin32 opencv-python mss keyboard
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
import json
import datetime
import subprocess
import gc
import re
import shutil
import ctypes
from datetime import timezone, timedelta

# ── Optional imports ──────────────────────────────────────────────────────────
WIN32_AVAILABLE = False
WIN32_ERROR = ""
try:
    import win32gui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except Exception as e:
    WIN32_ERROR = str(e)

try:
    from PIL import Image, ImageTk
    import numpy as np
    import cv2
    import mss
    CAPTURE_AVAILABLE = True
except Exception:
    CAPTURE_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except Exception:
    REQUESTS_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

try:
    import winsound
    SOUND_AVAILABLE = True
except Exception:
    SOUND_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except Exception:
    KEYBOARD_AVAILABLE = False

# ── Paths ─────────────────────────────────────────────────────────────────────
import sys as _sys
# Hard-coded version constant. This is the source of truth, NOT the config file.
# Config versions can be stale after updates, so we always check code version.
APP_VERSION = "1.3.8"
# Config and data MUST persist across exe locations. Use %APPDATA% on Windows
# so if the user downloads a new exe to Downloads or wherever, it still finds
# the config from the old one. The exe itself can live anywhere.
if getattr(_sys, "frozen", False):
    # Running as compiled exe - use %APPDATA%\FistbornRaidAlarm
    _APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
    _BASE = os.path.join(_APPDATA, "FistbornRaidAlarm")
    os.makedirs(_BASE, exist_ok=True)
    # Migrate legacy config from exe folder if AppData doesn't have one yet
    _LEGACY_BASE = os.path.dirname(os.path.abspath(_sys.executable))
    _legacy_cfg = os.path.join(_LEGACY_BASE, "raid_bot_config.json")
    _new_cfg = os.path.join(_BASE, "raid_bot_config.json")
    if os.path.exists(_legacy_cfg) and not os.path.exists(_new_cfg):
        try:
            import shutil as _shutil
            _shutil.copy2(_legacy_cfg, _new_cfg)
            # Also migrate history file if present
            _legacy_hist = os.path.join(_LEGACY_BASE, "raid_history.json")
            _new_hist = os.path.join(_BASE, "raid_history.json")
            if os.path.exists(_legacy_hist) and not os.path.exists(_new_hist):
                _shutil.copy2(_legacy_hist, _new_hist)
        except Exception:
            pass
else:
    # Running as Python script - use script folder (dev convenience)
    _BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE     = os.path.join(_BASE, "raid_bot_config.json")
SCREENSHOTS_DIR = os.path.join(_BASE, "raid_screenshots")
HISTORY_FILE    = os.path.join(_BASE, "raid_history.json")
TRIGGER_FILE    = os.path.join(_BASE, "raid_trigger.txt")
# Template is bundled INSIDE the exe, so look there first, then fall back to disk
if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
    TEMPLATE_FILE = os.path.join(_sys._MEIPASS, "banner_template.png")
    if not os.path.exists(TEMPLATE_FILE):
        TEMPLATE_FILE = os.path.join(_BASE, "banner_template.png")
else:
    TEMPLATE_FILE = os.path.join(_BASE, "banner_template.png")

DEFAULT_CONFIG = {
    "webhook_url": "",
    "webhook_url_2": "",
    "webhook_url_3": "",
    "webhook_desc": "Primary gang server",
    "webhook_desc_2": "Ally #1",
    "webhook_desc_3": "Ally #2",
    "discord_message": "<@&870791568200704030> <@&870791620910538783> <@&1454940232712454297> RAID DETECTED! Join the server in the screenshot below or click the link below: https://www.roblox.com/users/9405149316/profile",
    "discord_message_2": "",
    "discord_message_3": "",
    "server_join_link": "https://www.roblox.com/users/9405149316/profile",
    "join_link_enabled": True,
    "roblox_cookie": "",
    "roblox_user_id": "9405149316",
    "auto_fetch_join_link": True,
    "roblox_username": "",
    "roblox_password_enc": "",
    "auto_login_enabled": False,
    "last_login_attempt": 0,
    "login_backoff_until": 0,
    "version": APP_VERSION,
    "update_check_enabled": True,
    "update_repo": "typekaiser/kaisers-raid-utility",
    "clip_enabled": True,
    "selected_window_title": "",
    "red_threshold": 50,
    "scan_interval": 1,
    "cooldown": 30,
    "detection_mode": "template_ocr",
    "raid_text_keywords": ["INVADED", "RAID", "ATTACK"],
    "template_confidence": 75,
    "sound_enabled": True,
    "screenshot_enabled": True,
    "pin_roblox_topmost": True,
    "auto_start": False,
    "minimize_on_start": False,
    "scan_zone": None,
    "hotkey": "f8",
    "anti_afk_enabled": False,
    "anti_afk_interval": 300,
    "ntfy_enabled": False,
    "ntfy_channel": "kaiser-raid-bot",
    "streamer_mode": False,
    "lite_mode": False,
    "first_launch_done": False,
    "stop_message_enabled": True,
    "stop_message": "⏸️ Bot paused - changing server, back soon.",
    "daily_summary_enabled": True,
    "leaderboard_enabled": True,
    "flash_taskbar": True,
    "sound_style": "beep",
    "scheduled_enabled": False,
    "sched_start_hour": 18,
    "sched_stop_hour": 2,
    "active_profile": "default",
}

# ── Colours ───────────────────────────────────────────────────────────────────
BG     = "#141421"
BG2    = "#1e1e2e"
BG3    = "#2a2a3d"
ACCENT = "#ff4d6d"
GREEN  = "#4ade80"
YELLOW = "#fbbf24"
TEXT   = "#f8f8ff"
SUB    = "#a0a0b8"
BORDER = "#2a2a2a"


# ── Config helpers ────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            # ALWAYS override version with the current code's version,
            # otherwise old configs keep stale version strings forever
            cfg["version"] = APP_VERSION
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ── Raid history ──────────────────────────────────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_history(history):
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-200:], f, indent=2)  # keep last 200
    except Exception:
        pass


# ── Window helpers ────────────────────────────────────────────────────────────
def list_windows_powershell():
    try:
        ps = ('Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | '
              'ForEach-Object { $_.Id.ToString() + "|" + $_.MainWindowTitle }')
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            timeout=8, stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        results = []
        for line in out.strip().splitlines():
            line = line.strip()
            if "|" not in line:
                continue
            pid_str, title = line.split("|", 1)
            try:
                results.append((int(pid_str.strip()), title.strip()))
            except ValueError:
                pass
        return results
    except Exception:
        return []


def get_windows(all_windows=False):
    if WIN32_AVAILABLE:
        results = []
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd).strip()
                if t and (all_windows or "Roblox" in t):
                    results.append((hwnd, t))
        win32gui.EnumWindows(cb, None)
        return results
    else:
        wins = list_windows_powershell()
        return wins if all_windows else [(p, t) for p, t in wins if "Roblox" in t]


def set_topmost(hwnd, topmost=True):
    if not WIN32_AVAILABLE or not hwnd:
        return
    try:
        flag = win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception:
        pass


def get_window_rect(handle):
    if WIN32_AVAILABLE:
        try:
            return win32gui.GetWindowRect(handle)
        except Exception:
            return None
    else:
        ps_lines = [
            "$pid2 = " + str(handle),
            "$p = Get-Process -Id $pid2 -ErrorAction SilentlyContinue",
            "if ($p -and $p.MainWindowHandle -ne 0) {",
            "    $hwnd = $p.MainWindowHandle",
            "    $sig = '[DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr h, out RECT r); [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }'",
            "    Add-Type -MemberDefinition $sig -Name W -Namespace W -ErrorAction SilentlyContinue",
            "    $r = New-Object W.W+RECT",
            "    [W.W]::GetWindowRect($hwnd, [ref]$r) | Out-Null",
            "    Write-Output \"$($r.L) $($r.T) $($r.R) $($r.B)\"",
            "}",
        ]
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "\n".join(ps_lines)],
                timeout=6, stderr=subprocess.DEVNULL
            ).decode().strip()
            if out:
                parts = out.split()
                if len(parts) == 4:
                    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        except Exception:
            pass
        return None


def get_all_monitors():
    """Return bounding box covering all monitors as (left, top, width, height)."""
    try:
        with mss.mss() as sct:
            # monitors[0] is the combined virtual screen
            m = sct.monitors[0]
            return m["left"], m["top"], m["width"], m["height"]
    except Exception:
        return 0, 0, 1920, 1080


# ── Scan zone picker ──────────────────────────────────────────────────────────
def pick_scan_zone(on_done):
    """
    Transparent overlay spanning ALL monitors.
    User drags to select region. Calls on_done(x1, y1, x2, y2).
    """
    ml, mt, mw, mh = get_all_monitors()

    overlay = tk.Toplevel()
    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.35)
    overlay.configure(bg="black")
    overlay.overrideredirect(True)  # no title bar
    overlay.geometry(f"{mw}x{mh}+{ml}+{mt}")

    canvas = tk.Canvas(overlay, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # Instruction text centred on primary monitor area
    canvas.create_text(
        mw // 2, 50,
        text="Drag to draw scan zone  |  ESC to cancel",
        fill="white", font=("Segoe UI", 18, "bold")
    )

    start = [0, 0]
    rect_id = [None]
    info_id = [None]

    def on_press(e):
        start[0], start[1] = e.x, e.y
        if rect_id[0]:
            canvas.delete(rect_id[0])
        if info_id[0]:
            canvas.delete(info_id[0])

    def on_drag(e):
        if rect_id[0]:
            canvas.delete(rect_id[0])
        if info_id[0]:
            canvas.delete(info_id[0])
        rect_id[0] = canvas.create_rectangle(
            start[0], start[1], e.x, e.y,
            outline="#e03c3c", width=3, fill="#e03c3c", stipple="gray25"
        )
        w = abs(e.x - start[0])
        h = abs(e.y - start[1])
        info_id[0] = canvas.create_text(
            e.x + 10, e.y + 10,
            text=f"{w}x{h}",
            fill="white", font=("Segoe UI", 12), anchor="nw"
        )

    def on_release(e):
        # Convert canvas coords back to absolute screen coords
        x1 = min(start[0], e.x) + ml
        y1 = min(start[1], e.y) + mt
        x2 = max(start[0], e.x) + ml
        y2 = max(start[1], e.y) + mt
        overlay.destroy()
        if x2 - x1 > 10 and y2 - y1 > 10:
            on_done(x1, y1, x2, y2)

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    overlay.bind("<Escape>", lambda e: overlay.destroy())
    overlay.focus_force()


# ── Capture ───────────────────────────────────────────────────────────────────
# Thread-local mss instances - each thread gets its own, avoiding srcdc errors
_tls = threading.local()

def get_mss():
    if not getattr(_tls, "sct", None):
        _tls.sct = mss.mss()
    return _tls.sct


def capture_region(x1, y1, x2, y2):
    """Capture an absolute screen region. Returns PIL Image or None."""
    if not CAPTURE_AVAILABLE:
        return None
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None
    try:
        sct = get_mss()
        raw = sct.grab({"top": y1, "left": x1, "width": w, "height": h})
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except Exception as e:
        _tls.sct = None  # reset this thread's instance on error
        print(f"[capture_region error] {e}")
        return None


def capture_window(handle):
    """Capture the full window region."""
    if not handle:
        return None
    rect = get_window_rect(handle)
    if not rect:
        return None
    l, t, r, b = rect
    return capture_region(l, t, r, b)


# ── Detection ─────────────────────────────────────────────────────────────────
# Cache loaded template to avoid reloading every scan
_template_cache = None
_template_mtime = 0

def load_template():
    """Load banner_template.png, return greyscale numpy array or None."""
    global _template_cache, _template_mtime
    if not os.path.exists(TEMPLATE_FILE):
        return None
    mtime = os.path.getmtime(TEMPLATE_FILE)
    if _template_cache is not None and mtime == _template_mtime:
        return _template_cache
    try:
        img = cv2.imread(TEMPLATE_FILE, cv2.IMREAD_GRAYSCALE)
        _template_cache = img
        _template_mtime = mtime
        return img
    except Exception:
        return None


def detect_template(img, confidence=75):
    """
    Use OpenCV template matching to find the raid banner.
    Searches at multiple scales to handle resolution differences.
    Returns (found, confidence_pct).
    """
    template = load_template()
    if template is None:
        return False, 0

    # Convert capture to greyscale
    arr = np.array(img)
    grey = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    th, tw = template.shape[:2]
    ih, iw = grey.shape[:2]

    best = 0.0
    # Wide scale range - template is 1141px, 1440p banner could be 2400px+
    # 0.3 to 3.0 covers virtually any resolution/window size combo
    for scale in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                  1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 2.0, 2.3, 2.5, 2.8, 3.0]:
        new_w = int(tw * scale)
        new_h = int(th * scale)
        if new_w > iw or new_h > ih or new_w < 10 or new_h < 10:
            continue
        resized = cv2.resize(template, (new_w, new_h))
        result = cv2.matchTemplate(grey, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        if max_val > best:
            best = max_val

    pct = int(best * 100)
    return pct >= confidence, pct

    if not OCR_AVAILABLE:
        return False, ""
    try:
        text = pytesseract.image_to_string(img).upper()
        for kw in keywords:
            if kw.strip().upper() in text:
                return True, kw.strip()
        return False, ""
    except Exception as e:
        return False, str(e)


# ── Discord ───────────────────────────────────────────────────────────────────
def detect_raid_text(img, keywords):
    """OCR-based raid detection - checks image text for raid keywords."""
    if not OCR_AVAILABLE:
        return False, ""
    try:
        text = pytesseract.image_to_string(img).upper()
        for kw in keywords:
            if kw.upper() in text:
                return True, kw
        return False, ""
    except Exception:
        return False, ""


def send_ntfy(channel, title, message, priority="high"):
    """Send a push notification via ntfy.sh. No auth required."""
    if not REQUESTS_AVAILABLE or not channel:
        return False
    try:
        url = f"https://ntfy.sh/{channel.strip().lstrip('/')}"
        headers = {
            "Title": title.encode('utf-8'),
            "Priority": priority,
            "Tags": "rotating_light",
        }
        resp = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
        return resp.status_code in (200, 201)
    except Exception:
        return False


def fetch_roblox_presence(user_id, cookie, debug=False):
    """Query Roblox presence API for a user's current server.

    Returns dict with keys: placeId, gameId (jobId), join_link, status
    Returns None if not in a game, cookie invalid, or any error.
    Status codes:
      0 = Offline
      1 = Online (website)
      2 = InGame (this is what we want)
      3 = InStudio
    """
    if not REQUESTS_AVAILABLE or not user_id or not cookie:
        return None

    # Sanitise cookie: strip whitespace, newlines, and surrounding quotes
    cookie = cookie.strip().strip('"').strip("'").strip()
    # Handle URL-encoding if present
    if "%7C" in cookie or "%3A" in cookie:
        import urllib.parse
        cookie = urllib.parse.unquote(cookie)

    # Build a raw Cookie header instead of using requests' cookie jar.
    # The cookie jar mangles cookies starting with "." which is what Roblox uses.
    cookie_header = f".ROBLOSECURITY={cookie}"

    try:
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com/",
            "Cookie": cookie_header,
        }

        # First verify the cookie works
        auth_check = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            headers=base_headers,
            timeout=10,
        )
        if auth_check.status_code == 401:
            return {"error": "cookie is invalid or expired - re-copy from browser",
                    "placeId": None,
                    "raw": f"401 unauthorised. Response: {auth_check.text[:200]}" if debug else None}
        if auth_check.status_code != 200:
            return {"error": f"cookie check failed HTTP {auth_check.status_code}",
                    "placeId": None,
                    "raw": auth_check.text[:200] if debug else None}
        auth_me = auth_check.json()
        auth_user_id = auth_me.get("id")

        # Get a CSRF token by making a throwaway POST that will fail with 403 + token
        csrf_token = ""
        try:
            csrf_resp = requests.post(
                "https://auth.roblox.com/v2/logout",
                headers=base_headers,
                timeout=10,
            )
            csrf_token = csrf_resp.headers.get("x-csrf-token", "")
        except Exception:
            pass

        post_headers = dict(base_headers)
        post_headers["Content-Type"] = "application/json"
        if csrf_token:
            post_headers["x-csrf-token"] = csrf_token

        # Query presence
        resp = requests.post(
            "https://presence.roblox.com/v1/presence/users",
            json={"userIds": [int(user_id)]},
            headers=post_headers,
            timeout=10,
        )

        # If we got a 403 about CSRF, retry with the new token
        if resp.status_code == 403 and "x-csrf-token" in resp.headers:
            post_headers["x-csrf-token"] = resp.headers["x-csrf-token"]
            resp = requests.post(
                "https://presence.roblox.com/v1/presence/users",
                json={"userIds": [int(user_id)]},
                headers=post_headers,
                timeout=10,
            )

        if resp.status_code != 200:
            return {"error": f"presence HTTP {resp.status_code}",
                    "placeId": None,
                    "raw": resp.text[:300] if debug else None,
                    "auth_user_id": auth_user_id}
        data = resp.json()
        arr = data.get("userPresences", [])
        if not arr:
            return {"error": "no presence data returned",
                    "placeId": None,
                    "raw": str(data)[:300] if debug else None,
                    "auth_user_id": auth_user_id}
        p = arr[0]
        user_presence_type = p.get("userPresenceType", 0)
        place_id = p.get("placeId")
        game_id = p.get("gameId")

        if user_presence_type != 2:
            return {
                "error": "user not in a game",
                "placeId": None,
                "userPresenceType": user_presence_type,
                "raw": str(p)[:300] if debug else None,
                "auth_user_id": auth_user_id,
            }

        if not place_id:
            msg = "placeId hidden by Roblox."
            if auth_user_id and str(auth_user_id) != str(user_id):
                msg += (f" Cookie owner is user ID {auth_user_id} but you queried {user_id}. "
                        "Query a user your cookie owns.")
            else:
                msg += " Check if you're in a reserved/private server."
            return {
                "error": msg,
                "placeId": None,
                "userPresenceType": user_presence_type,
                "raw": str(p)[:300] if debug else None,
                "auth_user_id": auth_user_id,
            }

        if game_id:
            # Discord markdown only supports http/https links, so we use the standard
            # roblox.com URL. This triggers roblox:// protocol handler in the browser.
            join_link = f"https://www.roblox.com/games/start?placeId={place_id}&gameInstanceId={game_id}"
            link_quality = "full (specific server)"
        else:
            join_link = f"https://www.roblox.com/games/{place_id}"
            link_quality = "partial (game only)"

        return {
            "placeId": place_id,
            "gameId": game_id,
            "join_link": join_link,
            "link_quality": link_quality,
            "userPresenceType": user_presence_type,
            "error": None,
            "auth_user_id": auth_user_id,
            "raw": str(p)[:300] if debug else None,
        }
    except Exception as e:
        return {"error": str(e), "placeId": None}


def send_discord(webhook_url, message=None, screenshot_path=None, embed=None, filename="raid.png"):
    if not REQUESTS_AVAILABLE or not webhook_url:
        return False, "No webhook / requests not installed", None
    try:
        # Add ?wait=true so Discord returns the message object with its ID
        url = webhook_url.rstrip("/")
        if "?" in url:
            url += "&wait=true"
        else:
            url += "?wait=true"

        if screenshot_path and os.path.exists(screenshot_path):
            payload = {}
            if message:
                payload["content"] = message
            if embed:
                embed["image"] = {"url": f"attachment://{filename}"}
                payload["embeds"] = [embed]
            with open(screenshot_path, "rb") as f:
                r = requests.post(
                    url,
                    data={"payload_json": json.dumps(payload)},
                    files={"file": (filename, f, "image/png")},
                    timeout=10
                )
        else:
            payload = {}
            if message:
                payload["content"] = message
            if embed:
                payload["embeds"] = [embed]
            r = requests.post(url, json=payload, timeout=10)

        msg_id = None
        if r.status_code in (200, 204):
            try:
                msg_id = r.json().get("id")
            except Exception:
                pass
        return r.status_code in (200, 204), f"HTTP {r.status_code}", msg_id
    except Exception as e:
        return False, str(e), None


def delete_discord_message(webhook_url, message_id):
    """Delete a specific message sent via webhook."""
    if not REQUESTS_AVAILABLE or not webhook_url or not message_id:
        return
    try:
        url = webhook_url.rstrip("/") + f"/messages/{message_id}"
        requests.delete(url, timeout=10)
    except Exception:
        pass


def play_sound(style="beep"):
    if not SOUND_AVAILABLE:
        return
    try:
        if style == "beep":
            for _ in range(3):
                winsound.Beep(1200, 200)
                time.sleep(0.1)
        elif style == "alarm":
            for freq in [800, 1000, 1200, 1000, 800]:
                winsound.Beep(freq, 150)
                time.sleep(0.05)
        elif style == "pulse":
            for _ in range(6):
                winsound.Beep(900, 80)
                time.sleep(0.08)
        elif style == "none":
            pass
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════════════════════
class RaidBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"TYPE://KAISERS RAID UTILITY  v{APP_VERSION}")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.geometry("700x920")
        self.root.minsize(380, 400)

        self.cfg             = load_config()
        self.history         = load_history()
        self.running         = False
        self.paused          = False
        self.scan_thread     = None
        self.last_alert_time = 0
        self.selected_handle = None
        self.alert_count     = 0
        self.start_time      = time.time()
        self.session_raid_count = 0
        self.session_start_date = datetime.date.today()
        self._session_message_ids = []
        self._roblox_windows = []
        self._hotkey_id      = None
        self._calibrating    = False
        self._frame_buffer   = []  # ring buffer of (timestamp, PIL.Image) for clip feature
        self._frame_buffer_max = 20
        self._dev_unlocked   = False

        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        self._build_ui()
        # Show setup wizard on first launch
        if not self.cfg.get("first_launch_done"):
            self.root.after(500, self._show_setup_wizard)
        # Check for updates 3 seconds after launch
        self.root.after(3000, self._check_for_updates)
        # Start scheduled watch hours loop
        threading.Thread(target=self._scheduled_loop, daemon=True).start()
        self.root.after(300, self._startup_log)
        self.root.after(500, self._refresh_windows)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Startup ───────────────────────────────────────────────────────────────

    def _startup_log(self):
        self.log("TYPE://KAISERS RAID UTILITY V1 ALPHA ready", "green")
        if WIN32_AVAILABLE:
            self.log("win32gui: OK", "green")
        else:
            self.log(f"win32gui unavailable - PowerShell fallback active", "yellow")
        self.log(f"OCR: {'ready' if OCR_AVAILABLE else 'not available'}", "green" if OCR_AVAILABLE else "yellow")
        self.log(f"Hotkey: {'ready (' + self.cfg['hotkey'] + ')' if KEYBOARD_AVAILABLE else 'keyboard lib not installed - run: pip install keyboard'}", 
                 "green" if KEYBOARD_AVAILABLE else "yellow")

        zone = self.cfg.get("scan_zone")
        if zone:
            x1, y1, x2, y2 = zone
            self.zone_lbl.config(text=f"Zone: ({x1},{y1})→({x2},{y2}) [{x2-x1}x{y2-y1}px]", fg=GREEN)

        self._register_hotkey()

        if self.cfg.get("auto_start"):
            self.log("Auto-start enabled...", "green")
            self.root.after(1500, self._auto_start_when_ready)

    def _auto_start_when_ready(self):
        if self.selected_handle:
            self._start()
            if self.cfg.get("minimize_on_start"):
                self.root.iconify()
        else:
            self.root.after(1000, self._auto_start_when_ready)

    def _on_close(self):
        # Auto-save settings before closing
        try:
            save_config(self.cfg)
        except Exception:
            pass
        self._unregister_hotkey()
        self.running = False
        self.root.destroy()

    # ── Hotkey ────────────────────────────────────────────────────────────────

    def _register_hotkey(self):
        if not KEYBOARD_AVAILABLE:
            return
        self._unregister_hotkey()
        hk = self.cfg.get("hotkey", "f8").strip()
        if not hk:
            self.log("No hotkey set - skipping.", "yellow")
            return
        try:
            keyboard.add_hotkey(hk, self._hotkey_fired)
            self.log(f"Hotkey registered: {hk.upper()} = manual ping", "green")
        except Exception as e:
            self.log(f"Hotkey error: {e}", "yellow")

    def _unregister_hotkey(self):
        if not KEYBOARD_AVAILABLE:
            return
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

    def _hotkey_fired(self):
        """Called from keyboard thread - schedule on main thread."""
        self.root.after(0, self._manual_alert)

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top header bar ────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=ACCENT, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"TYPE://KAISERS RAID UTILITY  v{APP_VERSION}",
                 bg=ACCENT, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=14)
        self.status_lbl = tk.Label(hdr, text="  OFFLINE", bg=ACCENT, fg="white",
                                    font=("Segoe UI", 11, "bold"))
        self.status_lbl.pack(side="right", padx=14)
        self._compact = False
        tk.Button(hdr, text="⊡", bg=ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 13), cursor="hand2",
                  command=self._toggle_compact).pack(side="right", padx=4)

        # ── Notebook style ─────────────────────────────────────────────────────
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG3, foreground=TEXT,
                        padding=[16, 6], font=("Segoe UI", 11, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._tab_home(self.nb)
        self._tab_advanced(self.nb)

        # Global mousewheel handler
        def _global_scroll(e):
            widget = e.widget
            while widget:
                try:
                    widget.yview_scroll(int(-1*(e.delta/120)), "units")
                    return
                except Exception:
                    pass
                try:
                    widget = widget.master
                except Exception:
                    break
        self.root.bind_all("<MouseWheel>", _global_scroll)

    # ── HOME TAB ──────────────────────────────────────────────────────────────

    def _tab_home(self, nb):
        outer = tk.Frame(nb, bg=BG)
        nb.add(outer, text="  🏠 HOME  ")

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=f, anchor="nw")
        def _on_frame_configure(e): canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(e): canvas.itemconfig(win_id, width=e.width)
        f.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # ── STATUS BANNER ─────────────────────────────────────────────────────
        self.watch_frame = tk.Frame(f, bg=BG3)
        self.watch_frame.pack(fill="x", padx=8, pady=(8, 4))
        banner_inner = tk.Frame(self.watch_frame, bg=BG3, pady=16)
        banner_inner.pack(fill="x")
        self.watch_dot = tk.Label(banner_inner, text="⬤", bg=BG3, fg=SUB,
                                   font=("Segoe UI", 20, "bold"))
        self.watch_dot.pack(side="left", padx=(16, 8))
        self.watch_lbl = tk.Label(banner_inner, text="Bot is offline",
                                   bg=BG3, fg=SUB, font=("Segoe UI", 16, "bold"))
        self.watch_lbl.pack(side="left")
        self.watch_scan_lbl = tk.Label(banner_inner, text="",
                                        bg=BG3, fg=SUB, font=("Segoe UI", 9))
        self.watch_scan_lbl.pack(side="right", padx=4)
        stuck_btn = tk.Button(banner_inner, text="❓ Help",
                              bg=YELLOW, fg=BG, relief="flat",
                              font=("Segoe UI", 9, "bold"), cursor="hand2",
                              command=self._toggle_help_section)
        stuck_btn.pack(side="right", padx=(4, 16))

        # ── 4 BIG CONTROL BUTTONS ─────────────────────────────────────────────
        ctrl = tk.Frame(f, bg=BG); ctrl.pack(fill="x", padx=8, pady=(4, 4))
        self.start_btn = tk.Button(ctrl, text="▶  START",
                                    bg=GREEN, fg="white", relief="flat",
                                    font=("Segoe UI", 13, "bold"),
                                    cursor="hand2", pady=12,
                                    command=self._start)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.stop_btn = tk.Button(ctrl, text="■  STOP",
                                   bg=ACCENT, fg="white", relief="flat",
                                   font=("Segoe UI", 13, "bold"),
                                   cursor="hand2", pady=12, state="disabled",
                                   command=self._stop)
        self.stop_btn.pack(side="left", fill="x", expand=True, padx=3)
        self.pause_btn = tk.Button(ctrl, text="⏸  PAUSE",
                                    bg=YELLOW, fg=BG, relief="flat",
                                    font=("Segoe UI", 13, "bold"),
                                    cursor="hand2", pady=12, state="disabled",
                                    command=self._pause)
        self.pause_btn.pack(side="left", fill="x", expand=True, padx=3)
        tk.Button(ctrl, text="🚨  PING",
                  bg="#ff4400", fg="white", relief="flat",
                  font=("Segoe UI", 13, "bold"),
                  cursor="hand2", pady=12,
                  command=self._manual_alert).pack(side="left", fill="x", expand=True, padx=(3, 0))

        # ── QUICK ACTIONS ROW ─────────────────────────────────────────────────
        qa = tk.Frame(f, bg=BG); qa.pack(fill="x", padx=8, pady=(0, 6))
        tk.Button(qa, text="🎯 Update Server Link",
                  bg="#5865F2", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), cursor="hand2", pady=6,
                  command=self._quick_update_join_link).pack(side="left", fill="x", expand=True, padx=(0, 3))
        tk.Button(qa, text="🧪 Fire Test Alert",
                  bg=YELLOW, fg=BG, relief="flat",
                  font=("Segoe UI", 10, "bold"), cursor="hand2", pady=6,
                  command=self._test_alert).pack(side="left", fill="x", expand=True, padx=(3, 0))

        # ── ROBLOX WINDOW ─────────────────────────────────────────────────────
        sec = self._section(f, "🎮  Roblox Window")
        row = tk.Frame(sec, bg=BG2); row.pack(fill="x", pady=(0, 4))
        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(row, textvariable=self.window_var,
                                          state="readonly", width=42, font=("Segoe UI", 10))
        self.window_combo.pack(side="left", padx=(0, 6), fill="x", expand=True)
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_select)
        self._btn(row, "🔄 Refresh", self._refresh_windows, ACCENT).pack(side="left")

        # ── PRIMARY WEBHOOK ───────────────────────────────────────────────────
        sec_wh = self._section(f, "📣  Discord Webhook")
        self._field(sec_wh, "Webhook URL:", "webhook_url", width=54)
        self._field(sec_wh, "Alert Message:", "discord_message", width=54)
        wh_btns = tk.Frame(sec_wh, bg=BG2); wh_btns.pack(fill="x", pady=(4, 0))
        self._btn(wh_btns, "📋 Paste URL", self._paste_webhook, BG3).pack(side="left", padx=(0, 4))
        self._btn(wh_btns, "⚡ Quick Setup", self._quick_setup, GREEN).pack(side="left")
        self._btn(wh_btns, "Test Webhook", self._test_webhook, "#5865F2").pack(side="right")

        # ── SIMPLE TOGGLES ────────────────────────────────────────────────────
        sec_tog = self._section(f, "⚙️  Quick Settings")
        self.sound_var = tk.BooleanVar(value=self.cfg.get("sound_enabled", True))
        self.anti_afk_var = tk.BooleanVar(value=self.cfg.get("anti_afk_enabled", False))
        self.ntfy_var = tk.BooleanVar(value=self.cfg.get("ntfy_enabled", False))
        self.screenshot_var = tk.BooleanVar(value=self.cfg.get("screenshot_enabled", True))
        tog_row1 = tk.Frame(sec_tog, bg=BG2); tog_row1.pack(fill="x")
        tog_row2 = tk.Frame(sec_tog, bg=BG2); tog_row2.pack(fill="x", pady=(4, 0))
        for text, var in [
            ("🔊  Sound alerts",         self.sound_var),
            ("🛡️  Anti-AFK",             self.anti_afk_var),
        ]:
            tk.Checkbutton(tog_row1, text=text, variable=var, bg=BG2, fg=TEXT,
                           selectcolor=BG3, activebackground=BG2,
                           font=("Segoe UI", 10), cursor="hand2").pack(side="left", padx=(0, 16))
        for text, var in [
            ("📱  Mobile push (ntfy)",    self.ntfy_var),
            ("📸  Save screenshots",      self.screenshot_var),
        ]:
            tk.Checkbutton(tog_row2, text=text, variable=var, bg=BG2, fg=TEXT,
                           selectcolor=BG3, activebackground=BG2,
                           font=("Segoe UI", 10), cursor="hand2").pack(side="left", padx=(0, 16))
        tk.Button(sec_tog, text="💾  Save Settings",
                  bg=GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), cursor="hand2", pady=6,
                  command=self._save_settings).pack(fill="x", pady=(8, 0))

        # ── STATS ROW ─────────────────────────────────────────────────────────
        stats_frame = tk.Frame(f, bg=BG)
        stats_frame.pack(fill="x", padx=8, pady=(6, 4))
        self._big_stat(stats_frame, "🚨", "Alerts", "0", "stat_alerts")
        self._big_stat(stats_frame, "⏱", "Uptime", "00:00", "stat_uptime")
        self._big_stat(stats_frame, "🔴", "Pixels", "0", "stat_pixels")
        self._big_stat(stats_frame, "🕐", "Last", "-", "stat_last")

        # ── COOLDOWN BAR ──────────────────────────────────────────────────────
        cd_frame = tk.Frame(f, bg=BG2)
        cd_frame.pack(fill="x", padx=8, pady=4)
        cd_inner = tk.Frame(cd_frame, bg=BG2, pady=4); cd_inner.pack(fill="x", padx=8)
        tk.Label(cd_inner, text="Cooldown", bg=BG2, fg=SUB,
                 font=("Segoe UI", 9)).pack(side="left")
        self.cd_bar = ttk.Progressbar(cd_inner, orient="horizontal",
                                       mode="determinate", maximum=100, value=0)
        self.cd_bar.pack(side="left", fill="x", expand=True, padx=8)
        self.cd_label = tk.Label(cd_inner, text="Ready", bg=BG2, fg=GREEN,
                                  font=("Segoe UI", 9), width=10)
        self.cd_label.pack(side="left")

        # ── PREVIEW ───────────────────────────────────────────────────────────
        prev_frame = tk.Frame(f, bg=BG2)
        prev_frame.pack(fill="both", expand=True, padx=8, pady=4)
        tk.Label(prev_frame, text="📹  Live Scan Preview",
                 bg=BG2, fg=SUB, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 0))
        self.preview_lbl = tk.Label(prev_frame, bg="#111",
                                    text="No preview yet - start the bot", fg=SUB,
                                    font=("Segoe UI", 10))
        self.preview_lbl.pack(padx=6, pady=(2, 6), fill="both", expand=True)

        # ── LOG SECTION (collapsible) ─────────────────────────────────────────
        log_header = tk.Frame(f, bg=BG); log_header.pack(fill="x", padx=8, pady=(8, 0))
        self._log_expanded = tk.BooleanVar(value=False)
        self._log_toggle_btn = tk.Button(log_header, text="▸ Show Log",
                                          bg=BG, fg=SUB, relief="flat",
                                          font=("Segoe UI", 9), cursor="hand2",
                                          command=self._toggle_log_section)
        self._log_toggle_btn.pack(anchor="w")
        self._log_container = tk.Frame(f, bg=BG)
        self.log_box = scrolledtext.ScrolledText(self._log_container, bg="#0a0a0a", fg=TEXT,
                                                  font=("Consolas", 9),
                                                  relief="flat", bd=0,
                                                  state="disabled", height=10,
                                                  wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=4)
        for tag, col in [("green", GREEN), ("red", ACCENT), ("yellow", YELLOW),
                          ("white", TEXT), ("grey", SUB)]:
            self.log_box.tag_config(tag, foreground=col)

        # ── HELP SECTION (collapsible) ────────────────────────────────────────
        help_header = tk.Frame(f, bg=BG); help_header.pack(fill="x", padx=8, pady=(4, 0))
        self._help_expanded = tk.BooleanVar(value=False)
        self._help_toggle_btn = tk.Button(help_header, text="▸ Show Help Guide",
                                           bg=BG, fg=SUB, relief="flat",
                                           font=("Segoe UI", 9), cursor="hand2",
                                           command=self._toggle_help_section)
        self._help_toggle_btn.pack(anchor="w")
        self._help_container = tk.Frame(f, bg=BG)
        help_box = scrolledtext.ScrolledText(self._help_container, bg=BG2, fg=TEXT,
                                              font=("Segoe UI", 10),
                                              relief="flat", bd=4, wrap="word",
                                              height=20)
        help_box.pack(fill="both", expand=True, padx=8, pady=4)
        help_box.insert("1.0", """
TYPE://KAISERS RAID UTILITY - GUIDE
Made by @_KAISUR_ on Discord
=========================================

QUICK START
-----------
1. Pick your Roblox window from the dropdown
2. Paste your Discord webhook URL
3. Click START

That is it. The bot does the rest.


BUTTONS
-------
START - begins watching for raids
STOP - ends the session, sends a summary to Discord
PAUSE - temporarily stops detection (use when changing servers)
PING - manually fires a raid alert right now
Update Server Link - paste a fresh server join link from your clipboard
Fire Test Alert - sends a test message to Discord to confirm everything works


QUICK SETTINGS
--------------
Sound alerts - plays a sound on your PC when a raid is detected
Anti-AFK - clicks inside Roblox every 5 minutes so your alt doesn't get kicked
Mobile push - sends a notification to your phone via the ntfy app (free)
Save screenshots - saves raid screenshots to a folder next to the exe


REQUIREMENTS
------------
This bot needs to run on a secondary Windows PC or via Remote Desktop (RDP).
Running it on your main gaming PC will interfere with your mouse.

You also need a Roblox alt account logged in on that secondary machine.
The alt sits in the gang base server so the bot can watch it for raids.
Your main account stays free for actual gameplay.


COMMON ISSUES
-------------
Bot not detecting raids - make sure the Roblox window is selected in the dropdown and banner_template.png is in the same folder as the exe.

False alerts - go to Advanced tab and increase the Template Confidence slider.

Anti-AFK not working - make sure the toggle is on above and the bot is running.

Settings keep resetting - make sure you are not running the exe from inside a zip file.

Mobile notifications not working - install the ntfy app, subscribe to the channel shown in the Advanced tab.


CONTACT
-------
Discord: @_KAISUR_
GitHub: https://github.com/typekaiser/kaisers-raid-utility
""")
        help_box.config(state="disabled")

        # Spacer at bottom so last element isn't right at the edge
        tk.Frame(f, bg=BG, height=20).pack()

    def _toggle_log_section(self):
        if self._log_expanded.get():
            self._log_container.pack_forget()
            self._log_toggle_btn.config(text="▸ Show Log")
            self._log_expanded.set(False)
        else:
            self._log_container.pack(fill="both", expand=True)
            self._log_toggle_btn.config(text="▾ Hide Log")
            self._log_expanded.set(True)

    def _toggle_help_section(self):
        if self._help_expanded.get():
            self._help_container.pack_forget()
            self._help_toggle_btn.config(text="▸ Show Help Guide")
            self._help_expanded.set(False)
        else:
            self._help_container.pack(fill="both", expand=True)
            self._help_toggle_btn.config(text="▾ Hide Help Guide")
            self._help_expanded.set(True)

    def _show_help_popup(self):
        self._toggle_help_section()

    def _big_stat(self, parent, icon, label, value, attr):
        """Helper to build a compact stat card."""
        card = tk.Frame(parent, bg=BG2)
        card.pack(side="left", fill="x", expand=True, padx=2)
        inner = tk.Frame(card, bg=BG2, pady=6); inner.pack(fill="both", expand=True)
        tk.Label(inner, text=icon, bg=BG2, fg=ACCENT,
                 font=("Segoe UI", 14)).pack()
        val_lbl = tk.Label(inner, text=value, bg=BG2, fg=TEXT,
                            font=("Segoe UI", 13, "bold"))
        val_lbl.pack()
        tk.Label(inner, text=label, bg=BG2, fg=SUB,
                 font=("Segoe UI", 8)).pack()
        setattr(self, attr, val_lbl)

    # ── ADVANCED TAB ─────────────────────────────────────────────────────────

    def _tab_advanced(self, nb):
        outer = tk.Frame(nb, bg=BG)
        nb.add(outer, text="  🔧 ADVANCED  ")

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        f = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=f, anchor="nw")
        def _on_frame_configure(e): canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(e): canvas.itemconfig(win_id, width=e.width)
        f.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # ── ALLY WEBHOOKS ─────────────────────────────────────────────────────
        sec = self._section(f, "📣  Discord - Ally Servers")
        tk.Label(sec, text="── ALLY #1 (optional) ──",
                 bg=BG2, fg=YELLOW, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self._field(sec, "Webhook URL:", "webhook_url_2", width=56)
        self._field(sec, "Alert Message:", "discord_message_2", width=56)
        tk.Label(sec, text="Leave the alert message blank to use the same message as primary.",
                 bg=BG2, fg=SUB, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 6))
        tk.Label(sec, text="── ALLY #2 (optional) ──",
                 bg=BG2, fg=YELLOW, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
        self._field(sec, "Webhook URL:", "webhook_url_3", width=56)
        self._field(sec, "Alert Message:", "discord_message_3", width=56)
        tk.Label(sec, text="Leave the alert message blank to use the same message as primary.",
                 bg=BG2, fg=SUB, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

        # ── QUICK JOIN LINK ───────────────────────────────────────────────────
        sec_join = self._section(f, "🎯  One-Click Join Link (auto-fetch)")
        self.join_enabled_var = tk.BooleanVar(value=self.cfg.get("join_link_enabled", True))
        self.auto_fetch_var = tk.BooleanVar(value=self.cfg.get("auto_fetch_join_link", True))
        tk.Checkbutton(sec_join, text="Include join link in raid alerts",
                       variable=self.join_enabled_var, bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10)).pack(anchor="w")
        tk.Checkbutton(sec_join, text="Auto-fetch current server on every raid (needs cookie below)",
                       variable=self.auto_fetch_var, bg=BG2, fg=GREEN, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10)).pack(anchor="w")
        uid_row = tk.Frame(sec_join, bg=BG2); uid_row.pack(fill="x", pady=(6, 0))
        tk.Label(uid_row, text="Roblox User ID:", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 10)).pack(side="left")
        self.roblox_uid_var = tk.StringVar(value=self.cfg.get("roblox_user_id", ""))
        tk.Entry(uid_row, textvariable=self.roblox_uid_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, font=("Consolas", 9), width=18,
                 relief="flat", bd=4).pack(side="left", padx=6)
        tk.Label(uid_row, text="(numeric ID from the profile URL)",
                 bg=BG2, fg=SUB, font=("Segoe UI", 8)).pack(side="left", padx=4)
        ck_row = tk.Frame(sec_join, bg=BG2); ck_row.pack(fill="x", pady=(6, 0))
        tk.Label(ck_row, text="Cookie (dev-locked):", bg=BG2, fg=SUB,
                 font=("Segoe UI", 10)).pack(side="left")
        self.cookie_var = tk.StringVar(value=self.cfg.get("roblox_cookie", ""))
        entry_state_ck = "normal" if getattr(self, "_dev_unlocked", False) else "readonly"
        entry_bg_ck    = BG3 if getattr(self, "_dev_unlocked", False) else BG2
        entry_fg_ck    = TEXT if getattr(self, "_dev_unlocked", False) else SUB
        self._cookie_entry = tk.Entry(ck_row, textvariable=self.cookie_var,
                                       bg=entry_bg_ck, fg=entry_fg_ck,
                                       insertbackground=TEXT, font=("Consolas", 9), width=38,
                                       relief="flat", bd=4, show="•",
                                       state=entry_state_ck, readonlybackground=BG2)
        self._cookie_entry.pack(side="left", padx=6, fill="x", expand=True)
        ck_btn_row = tk.Frame(sec_join, bg=BG2); ck_btn_row.pack(fill="x", pady=(4, 0))
        self._btn(ck_btn_row, "🧪 Test Fetch", self._test_presence_fetch, GREEN).pack(side="left", padx=2)
        self._btn(ck_btn_row, "❌ Clear Cookie", self._clear_cookie, BG3).pack(side="left", padx=2)
        jl_row = tk.Frame(sec_join, bg=BG2); jl_row.pack(fill="x", pady=(8, 0))
        tk.Label(jl_row, text="Manual fallback link:", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 9)).pack(side="left")
        self.join_link_var = tk.StringVar(value=self.cfg.get("server_join_link", ""))
        tk.Entry(jl_row, textvariable=self.join_link_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, font=("Consolas", 9), width=38,
                 relief="flat", bd=4).pack(side="left", padx=6, fill="x", expand=True)
        jl_btn_row = tk.Frame(sec_join, bg=BG2); jl_btn_row.pack(fill="x", pady=(4, 0))
        self._btn(jl_btn_row, "📋 Paste Fallback", self._paste_join_link, "#5865F2").pack(side="left", padx=2)
        self._btn(jl_btn_row, "❌ Clear", self._clear_join_link, BG3).pack(side="left", padx=2)

        # ── DETECTION TUNING ─────────────────────────────────────────────────
        sec2 = self._section(f, "🎯  Detection Tuning")
        self.mode_var = tk.StringVar(value="template_ocr")
        self.kw_var = tk.StringVar(value=", ".join(self.cfg.get("raid_text_keywords",
                                                                  ["INVADED", "RAID", "ATTACK"])))
        tpl_exists = os.path.exists(TEMPLATE_FILE)
        self.tpl_lbl = tk.Label(sec2,
            text=f"{'✓ banner_template.png loaded' if tpl_exists else '✗ banner_template.png not found'}",
            bg=BG2, fg=GREEN if tpl_exists else ACCENT, font=("Segoe UI", 9))
        self.tpl_lbl.pack(anchor="w", pady=(0, 4))
        self._slider(sec2, "Template Confidence %:", "template_confidence", 50, 99)
        self._slider(sec2, "Scan Interval (sec):", "scan_interval", 1, 10)
        self._slider(sec2, "Alert Cooldown (sec):", "cooldown", 5, 300)

        # ── WINDOW OPTIONS ────────────────────────────────────────────────────
        sec_opts = self._section(f, "🪟  Window Options")
        self.show_all_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sec_opts, text="Show ALL windows (if Roblox not found)",
                       variable=self.show_all_var, bg=BG2, fg=YELLOW, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10),
                       command=self._refresh_windows).pack(anchor="w")
        self.topmost_var = tk.BooleanVar(value=self.cfg.get("pin_roblox_topmost", True))
        tk.Checkbutton(sec_opts, text="Pin selected window always-on-top",
                       variable=self.topmost_var, bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10),
                       command=self._apply_topmost).pack(anchor="w")

        # ── SCAN ZONE ─────────────────────────────────────────────────────────
        sec_zone = self._section(f, "🔍  Scan Zone")
        zrow = tk.Frame(sec_zone, bg=BG2); zrow.pack(fill="x", pady=(0, 4))
        self.zone_lbl = tk.Label(zrow, text="Full window (no zone set)",
                                  bg=BG2, fg=SUB, font=("Segoe UI", 10), anchor="w")
        self.zone_lbl.pack(side="left", expand=True, fill="x")
        self._btn(zrow, "Draw Zone", self._pick_zone, ACCENT).pack(side="left", padx=2)
        self._btn(zrow, "Clear", self._clear_zone, BG3).pack(side="left", padx=2)
        cal_row = tk.Frame(sec_zone, bg=BG2); cal_row.pack(fill="x")
        self.cal_btn = self._btn(cal_row, "Auto-Calibrate", self._auto_calibrate, YELLOW)
        self.cal_btn.pack(side="left")
        self.cal_lbl = tk.Label(cal_row, text="  Samples baseline red to set threshold",
                                 bg=BG2, fg=SUB, font=("Segoe UI", 8))
        self.cal_lbl.pack(side="left", padx=6)

        # ── HOTKEY ────────────────────────────────────────────────────────────
        sec_hk = self._section(f, "⌨️  Hotkey")
        hk_row = tk.Frame(sec_hk, bg=BG2); hk_row.pack(fill="x")
        tk.Label(hk_row, text="Manual ping key:", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 10)).pack(side="left")
        self.hotkey_var = tk.StringVar(value=self.cfg.get("hotkey", "f8"))
        tk.Entry(hk_row, textvariable=self.hotkey_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, font=("Segoe UI", 10), width=8,
                 relief="flat", bd=4).pack(side="left", padx=6)
        self._btn(hk_row, "Apply", self._apply_hotkey, ACCENT).pack(side="left")

        # ── ANTI-AFK ─────────────────────────────────────────────────────────
        sec_afk = self._section(f, "🛡️  Anti-AFK")
        self.anti_afk_var_adv = self.anti_afk_var  # same var as Home tab
        tk.Checkbutton(sec_afk, text="Enable anti-AFK (clicks Roblox every 5 minutes)",
                       variable=self.anti_afk_var, bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10)).pack(anchor="w")

        # ── AUTO-UPDATE ───────────────────────────────────────────────────────
        sec_update = self._section(f, "🔄  Auto-Update  🔒")
        self.update_check_var = tk.BooleanVar(value=self.cfg.get("update_check_enabled", True))
        tk.Checkbutton(sec_update, text="Check for updates on launch",
                       variable=self.update_check_var, bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10)).pack(anchor="w")
        upd_row = tk.Frame(sec_update, bg=BG2); upd_row.pack(fill="x", pady=(4, 0))
        tk.Label(upd_row, text="GitHub repo:", bg=BG2, fg=SUB,
                 font=("Segoe UI", 10)).pack(side="left")
        self.update_repo_var = tk.StringVar(value=self.cfg.get("update_repo", ""))
        entry_state = "normal" if getattr(self, "_dev_unlocked", False) else "readonly"
        entry_bg    = BG3 if getattr(self, "_dev_unlocked", False) else BG2
        entry_fg    = TEXT if getattr(self, "_dev_unlocked", False) else SUB
        self._repo_entry = tk.Entry(upd_row, textvariable=self.update_repo_var,
                                     bg=entry_bg, fg=entry_fg,
                                     insertbackground=TEXT, font=("Segoe UI", 10), width=30,
                                     relief="flat", bd=4, state=entry_state,
                                     readonlybackground=BG2)
        self._repo_entry.pack(side="left", padx=6)
        self._btn(upd_row, "Check Now", self._check_for_updates, "#5865F2").pack(side="left", padx=2)
        unlock_row = tk.Frame(sec_update, bg=BG2); unlock_row.pack(fill="x", pady=(4, 0))
        tk.Label(unlock_row, text="🔒 Dev-locked.",
                 bg=BG2, fg=SUB, font=("Segoe UI", 8)).pack(side="left")
        self._btn(unlock_row, "🔓 Unlock", self._unlock_dev_settings, "#5865F2").pack(side="left", padx=6)

        # ── MOBILE PUSH ───────────────────────────────────────────────────────
        sec_ntfy = self._section(f, "📱  Mobile Push (ntfy.sh)  🔒")
        self.ntfy_var_adv = self.ntfy_var  # same var as Home tab
        tk.Checkbutton(sec_ntfy, text="Enable mobile push notifications on raid",
                       variable=self.ntfy_var, bg=BG2, fg=TEXT, selectcolor=BG3,
                       activebackground=BG2, font=("Segoe UI", 10)).pack(anchor="w")
        ntfy_row = tk.Frame(sec_ntfy, bg=BG2); ntfy_row.pack(fill="x", pady=(4, 0))
        tk.Label(ntfy_row, text="Channel:", bg=BG2, fg=SUB,
                 font=("Segoe UI", 10)).pack(side="left")
        self.ntfy_channel_var = tk.StringVar(value=self.cfg.get("ntfy_channel", ""))
        self._ntfy_entry = tk.Entry(ntfy_row, textvariable=self.ntfy_channel_var,
                                     bg=entry_bg, fg=entry_fg,
                                     insertbackground=TEXT, font=("Segoe UI", 10), width=28,
                                     relief="flat", bd=4, state=entry_state,
                                     readonlybackground=BG2)
        self._ntfy_entry.pack(side="left", padx=6)
        self._btn(ntfy_row, "Test", self._test_ntfy, "#5865F2").pack(side="left", padx=2)
        tk.Label(sec_ntfy,
                 text="🔒 Channel locked. Subscribe to it in the ntfy app to receive raid alerts.",
                 bg=BG2, fg=SUB, font=("Segoe UI", 8),
                 wraplength=500, justify="left").pack(anchor="w", pady=(4, 0))

        # ── HISTORY / HEATMAP ─────────────────────────────────────────────────
        sec_hist = self._section(f, "📋  Raid History")
        self.history_box = scrolledtext.ScrolledText(sec_hist, bg="#0a0a0a", fg=TEXT,
                                                      font=("Consolas", 9),
                                                      relief="flat", bd=0,
                                                      state="disabled", height=8)
        self.history_box.pack(fill="both", expand=True, pady=(4, 0))
        self.heatmap_canvas = tk.Canvas(sec_hist, bg=BG2, height=120,
                                         highlightthickness=0)
        self.heatmap_canvas.pack(fill="x", pady=(8, 0))
        hist_btns = tk.Frame(sec_hist, bg=BG2); hist_btns.pack(fill="x", pady=(4, 0))
        self._btn(hist_btns, "🔄 Refresh", self._update_history_display, ACCENT).pack(side="left", padx=2)
        self._btn(hist_btns, "🗑 Clear History", self._clear_history, BG3).pack(side="left", padx=2)

        # ── CONFIG PROFILES ───────────────────────────────────────────────────
        sec_prof = self._section(f, "💾  Config Profiles")
        prof_row = tk.Frame(sec_prof, bg=BG2); prof_row.pack(fill="x")
        tk.Label(prof_row, text="Profile name:", bg=BG2, fg=TEXT,
                 font=("Segoe UI", 10)).pack(side="left")
        self.profile_var = tk.StringVar(value=self.cfg.get("active_profile", "default"))
        tk.Entry(prof_row, textvariable=self.profile_var, bg=BG3, fg=TEXT,
                 insertbackground=TEXT, font=("Segoe UI", 10), width=16,
                 relief="flat", bd=4).pack(side="left", padx=6)
        self._btn(prof_row, "💾 Save", self._save_profile, GREEN).pack(side="left", padx=2)
        self._btn(prof_row, "📂 Load", self._load_profile, "#5865F2").pack(side="left", padx=2)

        # ── TEST FUNCTIONS ────────────────────────────────────────────────────
        sec_test = self._section(f, "🧪  Test Functions")
        test_row = tk.Frame(sec_test, bg=BG2); test_row.pack(fill="x")
        self._btn(test_row, "🚨 Test Raid Alert", self._test_alert, "#5865F2", 20).pack(side="left", padx=4)
        self._btn(test_row, "Test Webhook", self._test_webhook, ACCENT).pack(side="left", padx=4)
        test_row2 = tk.Frame(sec_test, bg=BG2); test_row2.pack(fill="x", pady=(6, 0))
        self._btn(test_row2, "🔄 Test Update Flow", self._test_update_flow, YELLOW).pack(side="left", padx=4)
        tk.Label(test_row2, text="Simulates the update popup and download sequence",
                 bg=BG2, fg=SUB, font=("Segoe UI", 8)).pack(side="left", padx=6)

        # ── SAVE BUTTON ───────────────────────────────────────────────────────
        tk.Button(f, text="💾  Save All Settings",
                  bg=GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 12, "bold"), cursor="hand2", pady=10,
                  command=self._save_settings).pack(fill="x", padx=8, pady=12)

        tk.Frame(f, bg=BG, height=20).pack()


    # ── UI Helpers ────────────────────────────────────────────────────────────

    def _test_ntfy(self):
        channel = self.ntfy_channel_var.get().strip()
        if not channel:
            self.log("No ntfy channel set.", "red"); return
        def _send():
            ok = send_ntfy(channel, "🧪 TYPE://KAISERS Test",
                           "If you see this on your phone, ntfy is working.")
            self.log(f"Ntfy test: {'sent OK - check your phone' if ok else 'FAILED'}",
                     "green" if ok else "red")
        threading.Thread(target=_send, daemon=True).start()

    def _test_webhook(self):
        webhook = self._fv_webhook_url.get().strip()
        if not webhook:
            self._wh_status.config(text="● No URL set", fg=ACCENT)
            return
        self._wh_status.config(text="● Testing...", fg=YELLOW)
        def _check():
            embed = {
                "title": "✅  Webhook Connected",
                "description": "TYPE://KAISERS Raid Utility is connected to this channel.",
                "color": 0x3CE066,
                "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}"},
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            ok, info, _ = send_discord(webhook, None, embed=embed)
            self.root.after(0, lambda: self._wh_status.config(
                text=f"● {'Connected' if ok else 'Failed: ' + info}",
                fg=GREEN if ok else ACCENT))
        threading.Thread(target=_check, daemon=True).start()

    def _preview_sound(self):
        threading.Thread(target=lambda: play_sound(self.sound_style_var.get()), daemon=True).start()

    def _get_profile_names(self):
        profiles_dir = os.path.join(_BASE, "profiles")
        if not os.path.exists(profiles_dir):
            return "No profiles saved"
        names = [f.replace(".json","") for f in os.listdir(profiles_dir) if f.endswith(".json")]
        return "Profiles: " + ", ".join(names) if names else "No profiles saved"

    def _save_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            self.log("Enter a profile name first.", "yellow"); return
        profiles_dir = os.path.join(_BASE, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)
        path = os.path.join(profiles_dir, f"{name}.json")
        self._save_settings()
        with open(path, "w") as pf:
            json.dump(self.cfg, pf, indent=2)
        self.log(f"Profile '{name}' saved.", "green")
        self._profile_list_lbl.config(text=self._get_profile_names())

    def _load_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            self.log("Enter a profile name first.", "yellow"); return
        path = os.path.join(_BASE, "profiles", f"{name}.json")
        if not os.path.exists(path):
            self.log(f"Profile '{name}' not found.", "red"); return
        with open(path) as pf:
            loaded = json.load(pf)
        self.cfg.update(loaded)
        save_config(self.cfg)
        self.log(f"Profile '{name}' loaded. Restart to apply all settings.", "green")

    def _delete_profile(self):
        name = self.profile_var.get().strip()
        if not name:
            self.log("Enter a profile name first.", "yellow"); return
        path = os.path.join(_BASE, "profiles", f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            self.log(f"Profile '{name}' deleted.", "yellow")
            self._profile_list_lbl.config(text=self._get_profile_names())
        else:
            self.log(f"Profile '{name}' not found.", "red")

    def _reset_defaults(self):
        for key, val in DEFAULT_CONFIG.items():
            self.cfg[key] = val
        save_config(self.cfg)
        self.log("Settings reset to defaults. Restart to apply.", "yellow")

    def _scheduled_loop(self):
        """Auto start/stop bot based on scheduled hours."""
        while True:
            time.sleep(30)
            if not self.cfg.get("scheduled_enabled"):
                continue
            try:
                now_utc = datetime.datetime.now(timezone.utc)
                uk_offset = timedelta(hours=1) if 4 <= now_utc.month <= 10 else timedelta(hours=0)
                hour = (now_utc + uk_offset).hour
                start_h = self.cfg.get("sched_start_hour", 18)
                stop_h  = self.cfg.get("sched_stop_hour", 2)
                # Handle overnight ranges e.g. 18-02
                if start_h <= stop_h:
                    should_run = start_h <= hour < stop_h
                else:
                    should_run = hour >= start_h or hour < stop_h
                if should_run and not self.running:
                    self.root.after(0, self._start)
                    self.log(f"Scheduled auto-start at {hour:02}:00", "green")
                elif not should_run and self.running:
                    self.root.after(0, self._stop)
                    self.log(f"Scheduled auto-stop at {hour:02}:00", "yellow")
            except Exception:
                pass

    def _get_webhooks(self):
        """Return list of (url, description, message) tuples for all configured webhooks."""
        entries = []
        default_msg = self.cfg.get("discord_message", "")
        for key, desc_key, msg_key, default_desc in [
            ("webhook_url",   "webhook_desc",   "discord_message",   "Primary"),
            ("webhook_url_2", "webhook_desc_2", "discord_message_2", "Ally #1"),
            ("webhook_url_3", "webhook_desc_3", "discord_message_3", "Ally #2"),
        ]:
            u = (self.cfg.get(key) or "").strip()
            if u:
                desc = (self.cfg.get(desc_key) or default_desc).strip() or default_desc
                msg = (self.cfg.get(msg_key) or "").strip()
                if not msg:
                    msg = default_msg
                entries.append((u, desc, msg))
        return entries

    def _broadcast_discord(self, message=None, screenshot_path=None, embed=None, filename="raid.png"):
        """Send a Discord message to all configured webhooks.
        If `message` is None, uses each webhook's own alert message."""
        results = []
        for url, desc, wh_msg in self._get_webhooks():
            actual_msg = message if message is not None else wh_msg
            try:
                results.append(send_discord(url, actual_msg, screenshot_path, embed=embed, filename=filename))
            except Exception as e:
                results.append((False, str(e), None))
        return results

    def _check_for_updates(self, silent=False):
        """Check GitHub for a newer release. Shows popup if available.
        If silent=False, shows a 'Checking for updates...' popup that dismisses itself."""
        if not self.cfg.get("update_check_enabled", True):
            return
        repo = (self.cfg.get("update_repo") or "").strip()
        if not repo or "/" not in repo:
            return

        # Show "checking" popup if not silent
        status_popup = None
        status_label = None
        if not silent:
            status_popup = tk.Toplevel(self.root)
            status_popup.title("Checking for Updates")
            status_popup.geometry("320x110")
            status_popup.configure(bg=BG)
            status_popup.transient(self.root)
            status_popup.resizable(False, False)
            tk.Label(status_popup, text="🔄",
                     bg=BG, fg=ACCENT, font=("Segoe UI", 20, "bold")).pack(pady=(14, 0))
            status_label = tk.Label(status_popup,
                                     text="Checking for updates...",
                                     bg=BG, fg=TEXT, font=("Segoe UI", 11, "bold"))
            status_label.pack(pady=4)
            # Centre the popup
            status_popup.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 160
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 55
            status_popup.geometry(f"+{x}+{y}")

        def _close_status(msg=None, colour=None):
            if status_popup and status_popup.winfo_exists():
                if msg and status_label:
                    status_label.config(text=msg, fg=colour or TEXT)
                    status_popup.after(1500, status_popup.destroy)
                else:
                    status_popup.destroy()

        def _check():
            try:
                current_ver = APP_VERSION
                url = f"https://api.github.com/repos/{repo}/releases/latest"
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    self.root.after(0, lambda: _close_status("Could not check - no connection", YELLOW))
                    return
                data = resp.json()
                remote_ver = data.get("tag_name", "").lstrip("v").strip()
                if not remote_ver:
                    self.root.after(0, lambda: _close_status("No releases published yet", SUB))
                    return
                if self._version_newer(remote_ver, current_ver):
                    changelog = data.get("body", "")[:500] or "No changelog provided."
                    critical  = "critical" in (data.get("body", "").lower() or "")
                    download_url = ""
                    for asset in data.get("assets", []):
                        if asset.get("name", "").lower().endswith(".exe"):
                            download_url = asset.get("browser_download_url", "")
                            break
                    self.root.after(0, lambda: _close_status())
                    self.root.after(200, lambda: self._show_update_popup(
                        remote_ver, current_ver, changelog, download_url, critical))
                else:
                    self.root.after(0, lambda: _close_status(f"✅ You're up to date (v{current_ver})", GREEN))
            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: _close_status(f"Error: {err[:40]}", ACCENT))
                self.log(f"Update check failed: {err}", "grey")

        threading.Thread(target=_check, daemon=True).start()

    def _version_newer(self, a, b):
        """Return True if version string a is newer than b (e.g. '1.2.0' > '1.1.5')."""
        try:
            pa = [int(x) for x in a.split(".")]
            pb = [int(x) for x in b.split(".")]
            while len(pa) < len(pb): pa.append(0)
            while len(pb) < len(pa): pb.append(0)
            return pa > pb
        except Exception:
            return False

    def _show_update_popup(self, new_ver, cur_ver, changelog, download_url, critical):
        top = tk.Toplevel(self.root)
        top.title("Update Available")
        top.geometry("500x420")
        top.configure(bg=BG)
        top.transient(self.root)
        top.resizable(False, False)
        if critical:
            top.grab_set()

        # Centre popup
        top.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 210
        top.geometry(f"+{x}+{y}")

        tk.Label(top, text="🚀  Update Available!",
                 bg=BG, fg=ACCENT, font=("Segoe UI", 14, "bold")).pack(pady=(14, 4))
        tk.Label(top, text=f"v{cur_ver}  →  v{new_ver}",
                 bg=BG, fg=TEXT, font=("Segoe UI", 11)).pack()
        if critical:
            tk.Label(top, text="⚠️  CRITICAL UPDATE - install now",
                     bg=BG, fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(pady=(4, 0))

        tk.Label(top, text="What's new:", bg=BG, fg=SUB,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        cl = scrolledtext.ScrolledText(top, bg=BG2, fg=TEXT, font=("Segoe UI", 9),
                                        relief="flat", bd=4, wrap="word", height=7)
        cl.pack(fill="both", expand=True, padx=20)
        cl.insert("1.0", changelog)
        cl.config(state="disabled")

        # Progress bar (hidden until download starts)
        progress_frame = tk.Frame(top, bg=BG)
        progress_frame.pack(fill="x", padx=20, pady=(8, 0))
        progress_lbl = tk.Label(progress_frame, text="", bg=BG, fg=SUB,
                                 font=("Segoe UI", 9))
        progress_lbl.pack(anchor="w")
        progress_bar = ttk.Progressbar(progress_frame, orient="horizontal",
                                        mode="determinate", maximum=100, value=0)

        btn_row = tk.Frame(top, bg=BG); btn_row.pack(pady=10)

        def _start_update():
            """Download the exe, replace the old one, relaunch."""
            if not download_url:
                # No direct URL - fall back to opening browser
                import webbrowser
                repo = (self.cfg.get("update_repo") or "typekaiser/kaisers-raid-utility").strip()
                webbrowser.open(f"https://github.com/{repo}/releases/latest")
                top.destroy()
                return

            # Hide buttons, show progress bar
            update_btn.config(state="disabled", text="Downloading...")
            skip_btn.pack_forget() if not critical else None
            later_btn.pack_forget() if not critical else None
            progress_bar.pack(fill="x", pady=(4, 0))

            def _download():
                try:
                    import tempfile, shutil, subprocess, urllib.request

                    # Work out where the current exe lives
                    if getattr(_sys, "frozen", False):
                        current_exe = os.path.abspath(_sys.executable)
                    else:
                        # Running as .py - can't self-replace, open browser instead
                        self.root.after(0, lambda: _fallback_browser())
                        return

                    # Download to a temp file with progress tracking
                    tmp_dir  = tempfile.mkdtemp()
                    tmp_path = os.path.join(tmp_dir, "FistbornRaidAlarm_new.exe")

                    def _progress(block_num, block_size, total_size):
                        if total_size > 0:
                            pct = min(100, int(block_num * block_size * 100 / total_size))
                            self.root.after(0, lambda p=pct: _update_progress(p))

                    self.root.after(0, lambda: progress_lbl.config(text="Downloading update..."))
                    urllib.request.urlretrieve(download_url, tmp_path, _progress)
                    self.root.after(0, lambda: _update_progress(100))
                    self.root.after(0, lambda: progress_lbl.config(text="Installing..."))

                    # Write a batch script that:
                    # 1. Waits for this process to exit
                    # 2. Replaces the old exe with the new one
                    # 3. Launches the new exe
                    # 4. Deletes itself
                    bat_path = os.path.join(tmp_dir, "updater.bat")
                    bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
move /Y "{tmp_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
                    with open(bat_path, "w") as bat_f:
                        bat_f.write(bat_content)

                    # Launch the batch script hidden, then close ourselves
                    subprocess.Popen(
                        ["cmd.exe", "/c", bat_path],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        close_fds=True,
                    )
                    self.root.after(500, lambda: self.root.destroy())

                except Exception as e:
                    self.root.after(0, lambda err=str(e): _download_failed(err))

            def _update_progress(pct):
                progress_bar["value"] = pct
                progress_lbl.config(text=f"Downloading... {pct}%")

            def _download_failed(err):
                progress_lbl.config(text=f"Download failed: {err[:60]}", fg=ACCENT)
                update_btn.config(state="normal", text="Try Again")
                self.log(f"Update download failed: {err}", "red")

            def _fallback_browser():
                import webbrowser
                repo = (self.cfg.get("update_repo") or "typekaiser/kaisers-raid-utility").strip()
                webbrowser.open(f"https://github.com/{repo}/releases/latest")
                top.destroy()

            threading.Thread(target=_download, daemon=True).start()

        def _skip():
            self.cfg["skipped_version"] = new_ver
            save_config(self.cfg)
            top.destroy()

        update_btn = tk.Button(btn_row, text="⬇  Update Now",
                               command=_start_update,
                               bg=GREEN, fg="white", relief="flat",
                               font=("Segoe UI", 11, "bold"),
                               width=16, pady=8, cursor="hand2")
        update_btn.pack(side="left", padx=4)

        if not critical:
            skip_btn = tk.Button(btn_row, text="Skip Version",
                                  command=_skip,
                                  bg=BG3, fg=TEXT, relief="flat",
                                  font=("Segoe UI", 10), width=14, cursor="hand2")
            skip_btn.pack(side="left", padx=4)
            later_btn = tk.Button(btn_row, text="Remind Me Later",
                                   command=top.destroy,
                                   bg=BG3, fg=TEXT, relief="flat",
                                   font=("Segoe UI", 10), width=14, cursor="hand2")
            later_btn.pack(side="left", padx=4)

    def _unlock_dev_settings(self):
        """Prompt for dev password via custom popup, unlock dev fields if correct."""
        popup = tk.Toplevel(self.root)
        popup.title("Developer Unlock")
        popup.geometry("340x180")
        popup.configure(bg=BG)
        popup.transient(self.root)
        popup.grab_set()
        popup.resizable(False, False)

        # Centre
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 170
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 90
        popup.geometry(f"+{x}+{y}")

        tk.Label(popup, text="🔒  Developer Unlock",
                 bg=BG, fg=ACCENT, font=("Segoe UI", 13, "bold")).pack(pady=(14, 4))
        tk.Label(popup, text="Enter developer password:",
                 bg=BG, fg=TEXT, font=("Segoe UI", 10)).pack(pady=(4, 6))

        pw_var = tk.StringVar()
        entry = tk.Entry(popup, textvariable=pw_var, show="•",
                         bg=BG3, fg=TEXT, insertbackground=TEXT,
                         font=("Segoe UI", 12), width=20,
                         relief="flat", bd=4, justify="center")
        entry.pack(pady=4)
        entry.focus_set()

        status_lbl = tk.Label(popup, text="", bg=BG, fg=ACCENT,
                              font=("Segoe UI", 9))
        status_lbl.pack(pady=2)

        def _try_unlock(*_):
            import hashlib
            entered_hash = hashlib.sha256(pw_var.get().encode()).hexdigest()
            expected_hash = "b570307df9d4f111e678602156f2a715d9e0fae0dcc2e4be7aa2032022c40a8c"
            if entered_hash == expected_hash:
                self._dev_unlocked = True
                self.log("🔓 Developer settings unlocked.", "green")
                if hasattr(self, '_repo_entry'):
                    try:
                        self._repo_entry.config(state="normal",
                                                 readonlybackground=BG3, bg=BG3, fg=TEXT)
                    except Exception:
                        pass
                if hasattr(self, '_ntfy_entry'):
                    try:
                        self._ntfy_entry.config(state="normal",
                                                 readonlybackground=BG3, bg=BG3, fg=TEXT)
                    except Exception:
                        pass
                if hasattr(self, '_cookie_entry'):
                    try:
                        self._cookie_entry.config(state="normal",
                                                   readonlybackground=BG3, bg=BG3, fg=TEXT)
                    except Exception:
                        pass
                status_lbl.config(text="✅ Unlocked!", fg=GREEN)
                popup.after(800, popup.destroy)
            else:
                status_lbl.config(text="❌ Wrong password", fg=ACCENT)
                pw_var.set("")
                entry.focus_set()

        btn_row = tk.Frame(popup, bg=BG); btn_row.pack(pady=6)
        tk.Button(btn_row, text="Unlock", command=_try_unlock,
                  bg=GREEN, fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), width=10, cursor="hand2").pack(side="left", padx=4)
        tk.Button(btn_row, text="Cancel", command=popup.destroy,
                  bg=BG3, fg=TEXT, relief="flat",
                  font=("Segoe UI", 10), width=10, cursor="hand2").pack(side="left", padx=4)

        # Enter key triggers unlock
        entry.bind("<Return>", _try_unlock)

    def _show_help_popup(self):
        """Open the Help tab when user clicks Feeling Stuck."""
        try:
            # Find the help tab index by iterating tab texts
            for i in range(self.nb.index("end")):
                text = self.nb.tab(i, "text")
                if "ADVANCED" in text.upper() or "HOME" in text.upper():
                    self.nb.select(i)
                    self.log("Opened Help tab - read through for common questions.", "green")
                    return
        except Exception:
            pass

    def _toggle_compact(self):
        if not self._compact:
            self._compact = True
            self.nb.pack_forget()
            self._build_compact_ui()
            self.root.geometry("460x370")
            self.root.minsize(420, 340)
        else:
            self._compact = False
            if hasattr(self, "_compact_frame"):
                self._compact_frame.destroy()
            self.nb.pack(fill="both", expand=True)
            self.root.geometry("700x920")
            self.root.minsize(380, 400)

    def _build_compact_ui(self):
        f = tk.Frame(self.root, bg=BG, pady=4)
        f.pack(fill="both", expand=True)
        self._compact_frame = f

        # Back to full view button at top
        top_row = tk.Frame(f, bg=BG); top_row.pack(fill="x", padx=8, pady=(2,0))
        self._btn(top_row, "↩ Full View", self._toggle_compact, BG3, 10).pack(side="right")
        row1 = tk.Frame(f, bg=BG); row1.pack(fill="x", padx=8, pady=(4,1))
        tk.Label(row1, text="Win:", bg=BG, fg=SUB, font=("Segoe UI", 9)).pack(side="left")
        labels = [f"[{i+1}] {t}" for i, (_, t) in enumerate(self._roblox_windows)]
        self._compact_window_var = tk.StringVar()
        compact_combo = ttk.Combobox(row1, textvariable=self._compact_window_var,
                                     values=labels, state="readonly",
                                     width=18, font=("Segoe UI", 9))
        compact_combo.pack(side="left", padx=(3,6))
        idx = self.window_combo.current()
        if 0 <= idx < len(labels):
            compact_combo.current(idx)
        def _on_compact_window(*_):
            i = compact_combo.current()
            if 0 <= i < len(self._roblox_windows):
                self.selected_handle = self._roblox_windows[i][0]
                self.cfg["selected_window_title"] = self._roblox_windows[i][1]
        compact_combo.bind("<<ComboboxSelected>>", _on_compact_window)

        # ── Control buttons row ───────────────────────────────────────────────
        row2 = tk.Frame(f, bg=BG); row2.pack(fill="x", padx=8, pady=(4,1))
        self._btn(row2, "START",  self._start,        GREEN,     6).pack(side="left", padx=2)
        self._btn(row2, "STOP",   self._stop,         ACCENT,    6).pack(side="left", padx=2)
        self._btn(row2, "PAUSE",  self._pause,        YELLOW,    6).pack(side="left", padx=2)
        self._btn(row2, "PING",   self._manual_alert, "#ff4400", 6).pack(side="left", padx=2)

        # ── Test buttons row ──────────────────────────────────────────────────
        tk.Label(f, text="TEST FUNCTIONS", bg=BG, fg=SUB,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(4,0))
        row2b = tk.Frame(f, bg=BG); row2b.pack(fill="x", padx=8, pady=(1,2))
        self._btn(row2b, "🚨 Raid", self._test_alert, "#5865F2", 8).pack(side="left", padx=2)

        # ── Status bar ────────────────────────────────────────────────────────
        row3 = tk.Frame(f, bg=BG2, pady=3); row3.pack(fill="x", padx=8, pady=(4,1))
        self._compact_dot = tk.Label(row3, text="⬤", bg=BG2, fg=SUB, font=("Segoe UI", 10))
        self._compact_dot.pack(side="left", padx=(8,4))
        self._compact_status = tk.Label(row3, text="Bot is offline", bg=BG2, fg=SUB,
                                        font=("Segoe UI", 9))
        self._compact_status.pack(side="left", expand=True, anchor="w")
        # Cooldown indicator on the right of status bar
        self._compact_cd_lbl = tk.Label(row3, text="", bg=BG2, fg=SUB, font=("Segoe UI", 9))
        self._compact_cd_lbl.pack(side="right", padx=8)

        # ── Stats row ─────────────────────────────────────────────────────────
        row4 = tk.Frame(f, bg=BG); row4.pack(fill="x", padx=8, pady=(2,1))
        self._compact_alerts_lbl = tk.Label(row4, text="Alerts: 0", bg=BG, fg=TEXT,
                                            font=("Segoe UI", 9))
        self._compact_alerts_lbl.pack(side="left", padx=(0,8))
        self._compact_uptime_lbl = tk.Label(row4, text="Uptime: --:--:--", bg=BG, fg=TEXT,
                                            font=("Segoe UI", 9))
        self._compact_uptime_lbl.pack(side="left", padx=(0,8))
        self._compact_last_lbl = tk.Label(row4, text="Last: -", bg=BG, fg=SUB,
                                          font=("Segoe UI", 9))
        self._compact_last_lbl.pack(side="left", padx=(0,8))
        hk = self.cfg.get("hotkey", "f8").upper()
        tk.Label(row4, text=f"Hotkey: {hk}", bg=BG, fg=SUB,
                 font=("Segoe UI", 9)).pack(side="right")

        # ── Live preview ──────────────────────────────────────────────────────
        self._compact_preview = tk.Label(f, bg="#111", text="No preview yet",
                                         fg=SUB, font=("Segoe UI", 9))
        self._compact_preview.pack(fill="x", padx=8, pady=(3,4))

        self._compact_update_loop()

    def _compact_update_loop(self):
        """Keep compact stats, status and preview in sync."""
        if not self._compact or not hasattr(self, "_compact_frame") or not self._compact_frame.winfo_exists():
            return
        # Alerts
        if hasattr(self, "_compact_alerts_lbl"):
            self._compact_alerts_lbl.config(text=f"Alerts: {self.alert_count}")
        # Uptime
        if hasattr(self, "_compact_uptime_lbl"):
            if self.running and hasattr(self, "start_time"):
                secs = int(time.time() - self.start_time)
                self._compact_uptime_lbl.config(
                    text=f"Uptime: {secs//3600:02}:{(secs%3600)//60:02}:{secs%60:02}", fg=TEXT)
            else:
                self._compact_uptime_lbl.config(text="Uptime: --:--:--", fg=SUB)
        # Last alert
        if hasattr(self, "_compact_last_lbl") and hasattr(self, "stat_last"):
            last = self.stat_last.cget("text")
            self._compact_last_lbl.config(text=f"Last: {last}" if last != "-" else "Last: -")
        # Cooldown
        if hasattr(self, "_compact_cd_lbl") and self.running:
            elapsed = time.time() - self.last_alert_time
            cooldown = self.cfg.get("cooldown", 30)
            remaining = max(0, int(cooldown - elapsed))
            if remaining == 0:
                self._compact_cd_lbl.config(text="Ready", fg=GREEN)
            else:
                self._compact_cd_lbl.config(text=f"CD: {remaining}s", fg=YELLOW)
        # Status dot
        if hasattr(self, "_compact_dot") and hasattr(self, "_compact_status"):
            if self.paused:
                self._compact_dot.config(fg=YELLOW)
                self._compact_status.config(text="Paused - scanning suspended", fg=YELLOW)
            elif self.running:
                self._compact_dot.config(fg=GREEN)
                self._compact_status.config(text="Watching...", fg=GREEN)
            else:
                self._compact_dot.config(fg=SUB)
                self._compact_status.config(text="Bot is offline", fg=SUB)
        # Mirror live preview to compact
        if hasattr(self, "_compact_preview") and hasattr(self, "preview_lbl"):
            photo = getattr(self.preview_lbl, "_img", None)
            if photo:
                self._compact_preview.config(image=photo, text="")
                self._compact_preview._img = photo
        self.root.after(1000, self._compact_update_loop)

    def _section(self, parent, title):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", padx=10, pady=(6,2))
        tk.Label(outer, text=title, bg=BG, fg=SUB,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        inner = tk.Frame(outer, bg=BG2, highlightbackground=BORDER, highlightthickness=1)
        inner.pack(fill="x", pady=(2,0))
        pad = tk.Frame(inner, bg=BG2)
        pad.pack(fill="x", padx=8, pady=6)
        return pad

    def _btn(self, parent, text, cmd, colour=ACCENT, width=None):
        kw = {"width": width} if width else {}
        return tk.Button(parent, text=text, command=cmd, bg=colour,
                         fg="white" if colour not in (YELLOW, BG3) else (BG if colour==YELLOW else TEXT),
                         relief="flat", bd=0, cursor="hand2",
                         font=("Segoe UI", 10, "bold"), padx=10, pady=5, **kw)

    def _stat(self, parent, label, value):
        fr = tk.Frame(parent, bg=BG3, padx=10, pady=6)
        fr.pack(side="left", expand=True, fill="x", padx=3)
        tk.Label(fr, text=label, bg=BG3, fg=SUB, font=("Segoe UI", 8)).pack()
        lbl = tk.Label(fr, text=value, bg=BG3, fg=TEXT, font=("Segoe UI", 12, "bold"))
        lbl.pack()
        return lbl

    def _field(self, parent, label, key, width=40):
        tk.Label(parent, text=label, bg=BG2, fg=TEXT, font=("Segoe UI", 10)).pack(anchor="w")
        var = tk.StringVar(value=self.cfg.get(key, ""))
        setattr(self, f"_fv_{key}", var)
        tk.Entry(parent, textvariable=var, bg=BG3, fg=TEXT, insertbackground=TEXT,
                 font=("Segoe UI", 10), width=width, relief="flat", bd=4).pack(anchor="w", pady=(0,6))

    def _slider(self, parent, label, key, lo, hi):
        row = tk.Frame(parent, bg=BG2); row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=BG2, fg=TEXT, font=("Segoe UI", 10),
                 width=24, anchor="w").pack(side="left")
        var = tk.IntVar(value=self.cfg.get(key, lo))
        setattr(self, f"_sv_{key}", var)
        tk.Label(row, textvariable=var, bg=BG2, fg="#ff6b6b",
                 font=("Segoe UI", 10, "bold"), width=6).pack(side="right")
        tk.Scale(row, from_=lo, to=hi, orient="horizontal", variable=var,
                 bg=BG2, fg=TEXT, troughcolor=BG3, highlightthickness=0,
                 showvalue=False, length=190).pack(side="right")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _refresh_windows(self):
        show_all = self.show_all_var.get()
        wins = get_windows(all_windows=show_all)
        self._roblox_windows = wins
        labels = [f"[{i+1}] {t}" for i, (_, t) in enumerate(wins)]
        self.window_combo["values"] = labels
        if labels:
            # If we already have a handle selected, find it in the new list by handle
            # This preserves the user's manual selection across refreshes
            if self.selected_handle:
                idx = next((i for i, (h, _) in enumerate(wins) if h == self.selected_handle), None)
                if idx is not None:
                    self.window_combo.current(idx)
                    # Don't call _on_window_select - handle hasn't changed
                    self.log(f"Windows refreshed - keeping selected handle.", "green")
                    return
            # No handle selected yet - try to restore from saved title
            saved = self.cfg.get("selected_window_title", "")
            idx = next((i for i, (_, t) in enumerate(wins) if t == saved), 0)
            self.window_combo.current(idx)
            self._on_window_select()
            self.log(f"Found {len(wins)} window(s).", "green")
        else:
            self.log("No windows found. Tick 'Show ALL windows' and refresh.", "yellow")

    def _paste_join_link(self):
        try:
            text = self.root.clipboard_get().strip()
            if not text:
                self.log("Clipboard is empty.", "yellow"); return
            lower = text.lower()
            if not any(k in lower for k in ("roblox.com", "roblox://", "games/start", "ropro")):
                self.log(f"That doesn't look like a Roblox join link: {text[:60]}", "yellow"); return
            self.join_link_var.set(text)
            self.cfg["server_join_link"] = text
            save_config(self.cfg)
            self.log(f"✓ Join link updated: {text[:80]}", "green")
        except Exception as e:
            self.log(f"Could not read clipboard: {e}", "red")

    def _clear_join_link(self):
        self.join_link_var.set("")
        self.cfg["server_join_link"] = ""
        save_config(self.cfg)
        self.log("Join link cleared.", "yellow")

    def _clear_cookie(self):
        if not getattr(self, "_dev_unlocked", False):
            self.log("🔒 Dev-locked. Unlock first to modify cookie.", "yellow"); return
        self.cookie_var.set("")
        self.cfg["roblox_cookie"] = ""
        save_config(self.cfg)
        self.log("Cookie cleared.", "yellow")

    def _test_presence_fetch(self):
        uid    = self.roblox_uid_var.get().strip()
        cookie = self.cookie_var.get().strip()
        if not uid:
            self.log("❌ No user ID set.", "red"); return
        if not cookie:
            self.log("❌ No cookie set. Unlock dev settings and paste the cookie first.", "red"); return
        self.log("🔄 Testing presence fetch...", "white")
        def _run():
            result = fetch_roblox_presence(uid, cookie, debug=True)
            if not result:
                self.log("❌ Fetch failed completely.", "red"); return
            if result.get("auth_user_id"):
                match = str(result["auth_user_id"]) == str(uid)
                self.log(f"   Cookie logged in as user ID: {result['auth_user_id']}",
                         "green" if match else "yellow")
                if not match:
                    self.log(f"   ⚠ Cookie owner ({result['auth_user_id']}) != queried user ({uid})", "yellow")
            if result.get("raw"):
                self.log(f"   Raw: {result['raw']}", "white")
            if result.get("error"):
                self.log(f"❌ {result['error']}", "red")
                if result.get("userPresenceType") is not None:
                    s = {0:"Offline",1:"Online (website)",2:"In-Game",3:"In-Studio"}.get(result["userPresenceType"],"Unknown")
                    self.log(f"   Status: {s}", "yellow")
                return
            self.log(f"✅ SUCCESS - {result.get('link_quality','link built')}", "green")
            self.log(f"   placeId: {result['placeId']}", "green")
            self.log(f"   gameId:  {result.get('gameId') or '(missing)'}", "green" if result.get("gameId") else "yellow")
            self.log(f"   Link:    {result['join_link']}", "green")
            self.cfg["server_join_link"] = result["join_link"]
            if hasattr(self, "join_link_var"): self.join_link_var.set(result["join_link"])
            save_config(self.cfg)
            self.log("   ✓ Saved as fallback link.", "green")
        threading.Thread(target=_run, daemon=True).start()

    def _load_fields_from_cfg(self):
        """Reload all UI field variables from self.cfg after a preset/profile load."""
        for key, var_name in [
            ("webhook_url",        "_fv_webhook_url"),
            ("webhook_url_2",      "_fv_webhook_url_2"),
            ("webhook_url_3",      "_fv_webhook_url_3"),
            ("discord_message",    "_fv_discord_message"),
            ("discord_message_2",  "_fv_discord_message_2"),
            ("discord_message_3",  "_fv_discord_message_3"),
        ]:
            if hasattr(self, var_name):
                getattr(self, var_name).set(self.cfg.get(key, ""))
        if hasattr(self, "sound_var"):        self.sound_var.set(self.cfg.get("sound_enabled", True))
        if hasattr(self, "screenshot_var"):   self.screenshot_var.set(self.cfg.get("screenshot_enabled", True))
        if hasattr(self, "anti_afk_var"):     self.anti_afk_var.set(self.cfg.get("anti_afk_enabled", False))
        if hasattr(self, "ntfy_var"):         self.ntfy_var.set(self.cfg.get("ntfy_enabled", False))
        if hasattr(self, "update_check_var"): self.update_check_var.set(self.cfg.get("update_check_enabled", True))

    def _draw_heatmap(self):
        """Draw a 7-day x 24-hour heatmap on heatmap_canvas."""
        try:
            canvas = self.heatmap_canvas
            canvas.delete("all")
            w = canvas.winfo_width() or 500
            h = canvas.winfo_height() or 120
            if not self._history:
                canvas.create_text(w//2, h//2, text="No raid history yet",
                                   fill=SUB, font=("Segoe UI", 9))
                return
            import collections, datetime as dt
            counts = collections.defaultdict(int)
            for entry in self._history:
                try:
                    ts = entry.get("time", "")
                    d = dt.datetime.fromisoformat(ts)
                    counts[(d.weekday(), d.hour)] += 1
                except Exception:
                    pass
            max_count = max(counts.values()) if counts else 1
            cell_w = w / 24
            cell_h = (h - 20) / 7
            days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            for day in range(7):
                canvas.create_text(4, 20 + day * cell_h + cell_h/2,
                                   text=days[day], fill=SUB,
                                   font=("Segoe UI", 7), anchor="w")
            for hour in range(24):
                canvas.create_text(32 + hour * cell_w + cell_w/2, 8,
                                   text=str(hour), fill=SUB,
                                   font=("Segoe UI", 6))
            for day in range(7):
                for hour in range(24):
                    count = counts.get((day, hour), 0)
                    intensity = int(255 * count / max_count) if max_count else 0
                    r = min(255, 60 + intensity)
                    g = max(0, 80 - intensity // 2)
                    b = max(0, 80 - intensity // 2)
                    colour = f"#{r:02x}{g:02x}{b:02x}"
                    x1 = 32 + hour * cell_w
                    y1 = 20 + day * cell_h
                    canvas.create_rectangle(x1, y1, x1+cell_w-1, y1+cell_h-1,
                                            fill=colour, outline="")
        except Exception:
            pass

    def _test_update_flow(self):
        """Fire a fake update popup using the real latest release download URL
        so the full sequence (popup → progress bar → relaunch) can be tested."""
        repo = (self.cfg.get("update_repo") or "typekaiser/kaisers-raid-utility").strip()
        self.log("🔄 Fetching latest release URL for update flow test...", "white")
        def _fetch():
            try:
                url = f"https://api.github.com/repos/{repo}/releases/latest"
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    self.log(f"❌ Could not fetch release: HTTP {resp.status_code}", "red")
                    return
                data = resp.json()
                dl_url = ""
                for asset in data.get("assets", []):
                    if asset.get("name", "").lower().endswith(".exe"):
                        dl_url = asset.get("browser_download_url", "")
                        break
                changelog = "This is a test of the update flow.\n\nThe download bar and auto-relaunch are real.\nIf you click Update Now the bot will actually download the latest exe and relaunch."
                self.root.after(0, lambda: self._show_update_popup(
                    "TEST", APP_VERSION, changelog, dl_url, False))
                self.log("✓ Test update popup triggered. Check the popup window.", "green")
            except Exception as e:
                self.log(f"❌ Test update flow error: {e}", "red")
        threading.Thread(target=_fetch, daemon=True).start()

    def _quick_update_join_link(self):
        """Main-tab shortcut - paste clipboard as join link."""
        try:
            text = self.root.clipboard_get().strip()
            if not text:
                self.log("Clipboard empty. Copy a Roblox join link first.", "yellow")
                return
            lower = text.lower()
            if not any(k in lower for k in ("roblox.com", "roblox://", "games/start", "ropro")):
                self.log(f"Clipboard doesn't look like a Roblox link: {text[:60]}", "red")
                return
            self.cfg["server_join_link"] = text
            save_config(self.cfg)
            if hasattr(self, "join_link_var"):
                self.join_link_var.set(text)
            self.log(f"🎯 Join link updated: {text[:80]}", "green")
        except Exception as e:
            self.log(f"Could not update join link: {e}", "red")

    def _paste_webhook(self):
        try:
            text = self.root.clipboard_get().strip()
            if text:
                self._fv_webhook_url.set(text)
                self.log("Webhook URL pasted from clipboard.", "green")
            else:
                self.log("Clipboard is empty.", "yellow")
        except Exception:
            self.log("Could not read clipboard.", "yellow")

    def _quick_setup(self):
        """One-click preset optimised for Fistborn."""
        presets = {
            "detection_mode": "template_ocr",
            "template_confidence": 72,
            "scan_interval": 2,
            "cooldown": 30,
            "sound_enabled": True,
            "screenshot_enabled": True,
            "leaderboard_enabled": True,
            "anti_afk_enabled": True,
            "anti_afk_interval": 300,
        }
        self.cfg.update(presets)
        self._load_fields_from_cfg()
        save_config(self.cfg)
        self.log("Quick Setup applied - optimised for Fistborn raid detection.", "green")

    def _apply_hotkey(self):
        """Register the hotkey from the settings field."""
        key = self.hotkey_var.get().strip().lower()
        if not key:
            self.log("No hotkey entered.", "yellow")
            return
        try:
            keyboard.unhook_all_hotkeys()
            keyboard.add_hotkey(key, lambda: self.root.after(0, self._manual_alert))
            self.cfg["hotkey"] = key
            save_config(self.cfg)
            self.log(f"Hotkey registered: {key.upper()} = manual ping", "green")
        except Exception as e:
            self.log(f"Hotkey error: {e}", "red")

    def _update_history_display(self):
        """Refresh the history listbox and heatmap."""
        try:
            self.history_box.config(state="normal")
            self.history_box.delete("1.0", "end")
            for entry in reversed(self._history[-100:]):
                ts = entry.get("time", "")
                reason = entry.get("reason", "")
                self.history_box.insert("end", f"{ts}  {reason}\n")
            self.history_box.config(state="disabled")
            self._draw_heatmap()
        except Exception:
            pass

    def _on_window_select(self, *_):
        idx = self.window_combo.current()
        if 0 <= idx < len(self._roblox_windows):
            self.selected_handle = self._roblox_windows[idx][0]
            self.cfg["selected_window_title"] = self._roblox_windows[idx][1]
            self._apply_topmost()

    def _apply_topmost(self):
        set_topmost(self.selected_handle, self.topmost_var.get())

    def _test_alert(self):
        """Fire the full raid alert sequence but strip all @mentions so nobody gets pinged."""
        self.log("Running test alert sequence...", "white")
        # Fire ntfy test push if enabled
        if self.cfg.get("ntfy_enabled") and self.cfg.get("ntfy_channel"):
            def _test_push():
                ok = send_ntfy(self.cfg["ntfy_channel"],
                               "🧪 TYPE://KAISERS Test Alert",
                               "This is a test of the raid bot notification system. No real raid happened.",
                               priority="default")
                self.log(f"Ntfy test push: {'sent - check phone' if ok else 'FAILED'}",
                         "green" if ok else "yellow")
            threading.Thread(target=_test_push, daemon=True).start()

        def _fire():
            img = None
            zone = self.cfg.get("scan_zone")
            try:
                if zone:
                    img = capture_region(*zone)
                elif self.selected_handle:
                    img = capture_window(self.selected_handle)
            except Exception as e:
                self.log(f"Test capture error: {e}", "yellow")

            webhook = self.cfg.get("webhook_url", "")
            if not webhook:
                self.log("No webhook set - add one in Settings first.", "red")
                return

            # Screenshot + topbar stitch (same as real alert)
            screenshot_path = None
            if img is not None:
                fname = datetime.datetime.now().strftime("test_%Y%m%d_%H%M%S.png")
                screenshot_path = os.path.join(SCREENSHOTS_DIR, fname)
                try:
                    topbar_path = self._capture_topbar()
                    if topbar_path and os.path.exists(topbar_path):
                        with Image.open(topbar_path) as _tb:
                            topbar = _tb.copy()
                        ratio = img.width / topbar.width
                        new_h = int(topbar.height * ratio)
                        topbar_resized = topbar.resize((img.width, new_h), Image.LANCZOS)
                        combined = Image.new("RGB", (img.width, new_h + img.height))
                        combined.paste(topbar_resized, (0, 0))
                        combined.paste(img, (0, new_h))
                        combined.save(screenshot_path)
                        try: os.remove(topbar_path)
                        except: pass
                    else:
                        img.save(screenshot_path)
                except Exception:
                    screenshot_path = None

            # Build embed - same as real raid but clearly marked as test
            ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            uptime_secs = int(time.time() - self.start_time) if hasattr(self, "start_time") else 0
            uptime_str = f"{uptime_secs // 3600:02}:{(uptime_secs % 3600) // 60:02}:{uptime_secs % 60:02}"
            embed = {
                "title": "🧪  TEST ALERT - Not a real raid",
                "description": "This is a test of the raid detection system.",
                "color": 0x5865F2,
                "fields": [
                    {"name": "🔍 Detection Method", "value": "`Test trigger`",          "inline": True},
                    {"name": "🔢 Raid Count",        "value": "`#0 (test)`",            "inline": True},
                    {"name": "⏱️ Bot Uptime",        "value": f"`{uptime_str}`",        "inline": True},
                    {"name": "🕐 Triggered At",      "value": f"<t:{int(time.time())}:F>", "inline": False},
                ],
                "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}  •  Test mode"},
                "timestamp": ts_iso,
            }

            # Include the auto-fetched join link in the test too, so user can verify it works
            test_join_link = (self.cfg.get("server_join_link") or "").strip()
            if self.cfg.get("auto_fetch_join_link", True) and self.cfg.get("join_link_enabled", True):
                uid    = (self.cfg.get("roblox_user_id") or "").strip()
                cookie = (self.cfg.get("roblox_cookie") or "").strip()
                if uid and cookie:
                    self.log("🔄 Test: fetching current server link...", "white")
                    try:
                        fetched = fetch_roblox_presence(uid, cookie)
                        if fetched and fetched.get("join_link") and not fetched.get("error"):
                            test_join_link = fetched["join_link"]
                            self.log(f"   ✓ Got live server link", "green")
                        else:
                            err = (fetched or {}).get("error", "no response")
                            self.log(f"   ⚠ Auto-fetch failed: {err}", "yellow")
                            if fetched and fetched.get("userPresenceType") is not None:
                                status_map = {0: "Offline", 1: "Online (website)",
                                              2: "In-Game", 3: "In-Studio"}
                                s = status_map.get(fetched["userPresenceType"], "Unknown")
                                self.log(f"   User status: {s}", "yellow")
                    except Exception as e:
                        self.log(f"   ⚠ Auto-fetch error: {e}", "yellow")
                else:
                    self.log("   ⚠ Auto-fetch skipped: cookie or user ID missing", "yellow")
            if test_join_link and self.cfg.get("join_link_enabled", True):
                embed["fields"].append({
                    "name": "🎯 Join the Server (test)",
                    "value": f"[**→ Click here to join via ALERT's profile**]({test_join_link})\nClick Join on their profile page to get into the same server.",
                    "inline": False,
                })

            # Strip all @mentions from the alert message so nobody gets pinged
            safe_msg = re.sub(r"@(everyone|here|&?\d+)", "", self.cfg.get("discord_message", "")).strip()
            if not safe_msg:
                safe_msg = "Test alert fired."

            ok, info, _ = send_discord(webhook, safe_msg, screenshot_path, embed=embed)
            self.log(f"Test alert: {'sent OK' if ok else 'FAILED - ' + info}",
                     "green" if ok else "red")

            # Leaderboard capture
            self.log("Test: capturing leaderboard...", "white")
            lb_path = self._capture_leaderboard()
            if lb_path and os.path.exists(lb_path):
                lb_embed = {
                    "title": "📋  Test - Current Server List",
                    "description": "Everyone on the server at time of test.",
                    "color": 0x5865F2,
                    "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}  •  Test mode"},
                    "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                ok2, info2, _ = send_discord(webhook, None, lb_path, embed=lb_embed, filename="leaderboard.png")
                self.log(f"Test leaderboard: {'sent OK' if ok2 else 'FAILED - ' + info2}",
                         "green" if ok2 else "yellow")
                try: os.remove(lb_path)
                except: pass
            else:
                self.log("Test leaderboard: not captured.", "yellow")

        threading.Thread(target=_fire, daemon=True).start()

    def _save_settings(self):
        self.cfg["webhook_url"]           = self._fv_webhook_url.get().strip()
        self.cfg["webhook_url_2"]         = self._fv_webhook_url_2.get().strip()
        self.cfg["webhook_url_3"]         = self._fv_webhook_url_3.get().strip()
        self.cfg["discord_message"]       = self._fv_discord_message.get().strip()
        self.cfg["discord_message_2"]     = self._fv_discord_message_2.get().strip()
        self.cfg["discord_message_3"]     = self._fv_discord_message_3.get().strip()
        self.cfg["server_join_link"]      = self.join_link_var.get().strip()
        self.cfg["join_link_enabled"]     = self.join_enabled_var.get()
        self.cfg["auto_fetch_join_link"]  = self.auto_fetch_var.get()
        self.cfg["roblox_user_id"]        = self.roblox_uid_var.get().strip()
        if getattr(self, "_dev_unlocked", False):
            self.cfg["roblox_cookie"]     = self.cookie_var.get().strip()
        self.cfg["stop_message"]          = self._fv_stop_message.get().strip()
        # detection tuning sliders removed - stay at defaults
        self.cfg["sound_enabled"]         = self.sound_var.get()
        self.cfg["screenshot_enabled"]    = self.screenshot_var.get()
        self.cfg["stop_message_enabled"]  = self.stop_msg_var.get()
        self.cfg["daily_summary_enabled"] = self.daily_var.get()
        self.cfg["flash_taskbar"]         = self.flash_var.get()
        self.cfg["leaderboard_enabled"]   = self.lb_var.get()
        self.cfg["pin_roblox_topmost"]    = self.topmost_var.get()
        self.cfg["auto_start"]            = self.auto_start_var.get()
        self.cfg["minimize_on_start"]     = self.min_start_var.get()
        self.cfg["minimize_to_tray"]      = self.tray_var.get()
        # detection_mode is now always template_ocr
        self.cfg["detection_mode"]        = "template_ocr"
        self.cfg["hotkey"]                = self.hotkey_var.get().strip().lower()
        self.cfg["anti_afk_enabled"]      = self.anti_afk_var.get()
        # anti_afk_interval and scheduled hours stay at defaults
        self.cfg["ntfy_enabled"]          = self.ntfy_var.get()
        self.cfg["update_check_enabled"]  = self.update_check_var.get()
        if self._dev_unlocked:
            self.cfg["update_repo"]       = self.update_repo_var.get().strip()
            self.cfg["ntfy_channel"]      = self.ntfy_channel_var.get().strip()
        self.cfg["sound_style"]           = self.sound_style_var.get()
        save_config(self.cfg)
        self._register_hotkey()
        self.log("Settings saved.", "green")
        self.save_btn.config(text="Saved!")
        self.root.after(1500, lambda: self.save_btn.config(text="Save Settings"))

    def _pick_zone(self):
        self.log("Draw a box over the raid banner area. ESC to cancel.", "yellow")
        self.root.iconify()
        self.root.after(400, lambda: pick_scan_zone(self._on_zone_set))

    def _on_zone_set(self, x1, y1, x2, y2):
        self.root.deiconify()
        self.cfg["scan_zone"] = [x1, y1, x2, y2]
        save_config(self.cfg)
        self.zone_lbl.config(
            text=f"Zone: ({x1},{y1})→({x2},{y2}) [{x2-x1}x{y2-y1}px]", fg=GREEN)
        self.log(f"Scan zone set: ({x1},{y1}) to ({x2},{y2})", "green")

    def _clear_zone(self):
        self.cfg["scan_zone"] = None
        save_config(self.cfg)
        self.zone_lbl.config(text="Full window (no zone set)", fg=SUB)
        self.log("Scan zone cleared.", "yellow")

    def _auto_calibrate(self):
        """
        Sample red pixels for 5 seconds with no raid,
        then set threshold to 3x the peak observed.
        """
        if self._calibrating:
            return
        if not self.selected_handle and not self.cfg.get("scan_zone"):
            self.log("Select a window first before calibrating.", "red")
            return
        self._calibrating = True
        self.cal_btn.config(state="disabled", text="Calibrating...")
        self.log("Auto-calibrate: sampling for 5 seconds - make sure NO raid is showing!", "yellow")
        samples = []

        def _sample():
            for i in range(10):
                zone = self.cfg.get("scan_zone")
                if zone:
                    img = capture_region(*zone)
                else:
                    img = capture_window(self.selected_handle)
                if img:
                    samples.append(count_red_pixels(img))
                self.root.after(0, lambda i=i: self.cal_lbl.config(
                    text=f"  Sampling... {i+1}/10"))
                time.sleep(0.5)

            if samples:
                peak = max(samples)
                suggested = max(int(peak * 3), 500)
                # Update the slider
                self.root.after(0, lambda: self._sv_red_threshold.set(suggested))
                self.root.after(0, lambda: self.log(
                    f"Calibration done. Peak baseline: {peak}px → Threshold set to {suggested}", "green"))
                self.root.after(0, lambda: self.cal_lbl.config(
                    text=f"  Done! Threshold set to {suggested}"))
            else:
                self.root.after(0, lambda: self.log("Calibration failed - no capture.", "red"))

            self._calibrating = False
            self.root.after(0, lambda: self.cal_btn.config(
                state="normal", text="Auto-Calibrate Threshold"))

        threading.Thread(target=_sample, daemon=True).start()

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _clear_history(self):
        self.history = []
        save_history(self.history)
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        self.log("Raid history cleared.", "yellow")

    def _reload_history_ui(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        for i, entry in enumerate(reversed(self.history), 1):
            self.history_tree.insert("", "end", values=(
                entry.get("time", ""),
                entry.get("reason", ""),
                str(len(self.history) - i + 1)
            ))

    # ── Start / Stop ──────────────────────────────────────────────────────────

    def _start(self):
        if not CAPTURE_AVAILABLE:
            self.log("❌ Missing capture libraries (numpy/opencv/mss). Reinstall or rebuild exe.", "red")
            # Show a popup so it's impossible to miss
            import tkinter.messagebox as mb
            mb.showerror("Cannot Start", 
                         "Required libraries are missing:\n\nnumpy, opencv-python, mss\n\n"
                         "If running as exe: rebuild with PyInstaller.\n"
                         "If running as script: run: pip install numpy opencv-python mss")
            return
        if not self.selected_handle and not self.cfg.get("scan_zone"):
            self.log("❌ No Roblox window selected. Pick one from the dropdown on the HOME tab.", "red")
            import tkinter.messagebox as mb
            mb.showerror("Cannot Start", 
                         "No Roblox window selected.\n\n"
                         "Pick your Roblox window from the dropdown on the HOME tab, then try again.")
            return
        self._save_settings()
        self.running = True
        self.paused  = False
        self.start_time = time.time()
        self.alert_count = 0
        self.session_raid_count = 0
        self.session_start_date = datetime.date.today()
        self._session_message_ids = []
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.pause_btn.config(state="normal")
        self.status_lbl.config(text="  ACTIVE", fg="#aaffaa")
        self.log("Bot started.", "green")
        # Warn if template mode selected but no template file
        if self.cfg["detection_mode"] in ("template", "all") and not os.path.exists(TEMPLATE_FILE):
            self.log("WARNING: Template mode selected but banner_template.png not found!", "red")
        self._update_cooldown_bar()
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        self._update_uptime()
        self._animate_watch(0)
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        self._daily_thread = threading.Thread(target=self._daily_summary_loop, daemon=True)
        self._daily_thread.start()
        self._milestone_thread = threading.Thread(target=self._uptime_milestone_loop, daemon=True)
        self._milestone_thread.start()
        self._afk_thread = threading.Thread(target=self._anti_afk_loop, daemon=True)
        self._afk_thread.start()
        self._keepalive_thread = threading.Thread(target=self._send_keepalive, daemon=True)
        self._keepalive_thread.start()
        self._auto_refresh_loop()
        # Bot launch message
        webhook = self.cfg.get("webhook_url", "")
        if webhook:
            def _launch_msg():
                ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                embed = {
                    "title": "🟢  Bot is now Online",
                    "description": "TYPE://KAISERS Raid Utility has started. Watching the gang base.",
                    "color": 0x3CE066,
                    "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}"},
                    "timestamp": ts_iso,
                }
                _, _, msg_id = send_discord(webhook, None, embed=embed)
                if msg_id:
                    self._session_message_ids.append(msg_id)
            threading.Thread(target=_launch_msg, daemon=True).start()

    def _pause(self):
        if not self.paused:
            # Pausing
            self.paused = True
            self.pause_btn.config(text="RESUME")
            self.watch_dot.config(fg=YELLOW)
            self.watch_lbl.config(text="Bot paused - scanning suspended", fg=YELLOW)
            self.log("Bot paused. Heartbeat still active.", "yellow")
            # Send pause message to Discord
            webhook = self.cfg.get("webhook_url", "")
            if webhook and self.cfg.get("stop_message_enabled"):
                ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                uptime_secs = int(time.time() - self.start_time) if hasattr(self, "start_time") else 0
                uptime_str = f"{uptime_secs // 3600:02}:{(uptime_secs % 3600) // 60:02}:{uptime_secs % 60:02}"
                embed = {
                    "title": "⏸️  Bot Paused",
                    "description": self.cfg.get("stop_message", "Changing server, back soon."),
                    "color": 0xF0C040,
                    "fields": [
                        {"name": "⏱️ Session Uptime", "value": f"`{uptime_str}`",              "inline": True},
                        {"name": "🔢 Raids Detected", "value": f"`{self.session_raid_count}`", "inline": True},
                    ],
                    "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}  •  Scanning suspended"},
                    "timestamp": ts_iso,
                }
                threading.Thread(
                    target=lambda: send_discord(webhook, None, embed=embed),
                    daemon=True
                ).start()
        else:
            # Resuming
            self.paused = False
            self.pause_btn.config(text="PAUSE")
            self.log("Bot resumed. Scanning active.", "green")
            self._animate_watch(0)
            # Send resume notification
            webhook = self.cfg.get("webhook_url", "")
            if webhook:
                ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                embed = {
                    "title": "▶️  Bot Resumed",
                    "description": "🟢 Back online and watching the gang base.",
                    "color": 0x3CE066,
                    "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}"},
                    "timestamp": ts_iso,
                }
                threading.Thread(
                    target=lambda: send_discord(webhook, None, embed=embed),
                    daemon=True
                ).start()

    def _stop(self):
        self.running = False
        self.paused  = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        self.status_lbl.config(text="  OFFLINE", fg="white")
        self.watch_dot.config(fg=SUB)
        self.watch_lbl.config(text="Bot is offline", fg=SUB)
        self.watch_scan_lbl.config(text="")
        self.log("Bot stopped.", "yellow")

        webhook = self.cfg.get("webhook_url", "")
        if not webhook:
            return

        # Delete all messages from this session in background
        ids_to_delete = list(self._session_message_ids)
        self._session_message_ids.clear()

        def _cleanup():
            for mid in ids_to_delete:
                delete_discord_message(webhook, mid)
                time.sleep(0.3)
            if self.cfg.get("stop_message_enabled"):
                ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                uptime_secs = int(time.time() - self.start_time) if hasattr(self, "start_time") else 0
                uptime_str = f"{uptime_secs // 3600:02}:{(uptime_secs % 3600) // 60:02}:{uptime_secs % 60:02}"
                # Build raid time list from history for this session
                session_date = getattr(self, "session_start_date", datetime.date.today())
                session_raids = [e for e in self.history if e.get("time","").startswith(str(session_date))]
                raid_times = ", ".join(e["time"][11:16] for e in session_raids[-10:]) if session_raids else "None"
                embed = {
                    "title": "📊  Session Summary",
                    "description": self.cfg.get("stop_message", "Changing server, back soon."),
                    "color": 0xF0C040,
                    "fields": [
                        {"name": "⏱️ Session Uptime",    "value": f"`{uptime_str}`",              "inline": True},
                        {"name": "🔢 Raids Detected",    "value": f"`{self.session_raid_count}`", "inline": True},
                        {"name": "🕐 Raid Times (today)", "value": raid_times,                    "inline": False},
                    ],
                    "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}  •  Session ended"},
                    "timestamp": ts_iso,
                }
                send_discord(webhook, None, embed=embed)
                self.log("Session summary sent to Discord.", "yellow")

        threading.Thread(target=_cleanup, daemon=True).start()

    def _manual_alert(self):
        self.log("Manual alert triggered!", "red")
        def _fire():
            img = None
            zone = self.cfg.get("scan_zone")
            try:
                if zone:
                    img = capture_region(*zone)
                elif self.selected_handle:
                    rect = get_window_rect(self.selected_handle)
                    if rect:
                        with mss.mss() as sct:
                            l, t, r, b = rect
                            raw = sct.grab({"top": t, "left": l,
                                            "width": r-l, "height": b-t})
                            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            except Exception as e:
                self.log(f"Manual capture error: {e}", "yellow")
            self._trigger_alert(img, "Manual ping")
        threading.Thread(target=_fire, daemon=True).start()

    # ── Scan loop ─────────────────────────────────────────────────────────────

    def _scan_loop(self):
        while self.running:
            try:
                if not self.paused:
                    self._do_scan()
            except Exception as e:
                self.log(f"Scan error: {e}", "red")
            time.sleep(self.cfg["scan_interval"])

    def _do_scan(self):
        zone = self.cfg.get("scan_zone")
        if zone:
            img = capture_region(*zone)
        elif self.selected_handle:
            img = capture_window(self.selected_handle)
        else:
            self.log("No window selected and no scan zone set.", "red")
            self.running = False
            return

        if img is None:
            self.log("Could not capture - is Roblox visible and not minimised?", "yellow")
            return

        self.root.after(0, lambda i=img: self._update_preview(i))

        mode = self.mode_var.get()
        red_count = 0
        detected = False
        reason = ""

        # Template matching - fastest and most accurate
        if mode in ("template", "template_ocr", "all"):
            found, conf = detect_template(img, self.cfg.get("template_confidence", 75))
            self.log(f"Template confidence: {conf}%", "white")
            if found:
                detected = True
                reason = f"Template match: {conf}% confidence"

        # Red pixels
        if mode in ("red_pixels", "both", "all") and not detected:
            red_count = count_red_pixels(img)
            self.root.after(0, lambda c=red_count: self.stat_pixels.config(text=str(c)))
            if red_count >= self.cfg["red_threshold"]:
                detected = True
                reason = f"Red pixels: {red_count}"

        # OCR
        if mode in ("text", "both", "template_ocr", "all") and not detected:
            found, kw = detect_raid_text(img, self.cfg["raid_text_keywords"])
            if found:
                detected = True
                reason = f"Keyword: {kw}"

        alert_img = img.copy() if detected else None
        del img
        gc.collect()

        if detected:
            now = time.time()
            if now - self.last_alert_time >= self.cfg["cooldown"]:
                self.last_alert_time = now
                self.session_raid_count += 1
                self.log(f"RAID DETECTED! {reason} (raid #{self.session_raid_count} this session)", "red")
                self.root.after(0, self._animate_raid)
                self.root.after(0, self._flash_taskbar)
                threading.Thread(target=self._trigger_alert,
                                 args=(alert_img, reason), daemon=True).start()
            else:
                remaining = int(self.cfg["cooldown"] - (now - self.last_alert_time))
                self.log(f"Raid detected - cooldown {remaining}s", "yellow")

    def _trigger_alert(self, img, reason=""):
        self.alert_count += 1
        self.root.after(0, lambda: self.stat_alerts.config(text=str(self.alert_count)))
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.root.after(0, lambda: self.stat_last.config(text=ts[11:]))

        # Save to history
        entry = {"time": ts, "reason": reason}
        self.history.append(entry)
        save_history(self.history)
        self.root.after(0, self._reload_history_ui)

        # Screenshot
        screenshot_path = None
        if self.cfg["screenshot_enabled"] and img is not None:
            fname = datetime.datetime.now().strftime("raid_%Y%m%d_%H%M%S.png")
            screenshot_path = os.path.join(SCREENSHOTS_DIR, fname)
            try:
                # Try to capture the server info bar and stitch it above the raid screenshot
                topbar = None
                topbar_path = self._capture_topbar()
                if topbar_path and os.path.exists(topbar_path):
                    with Image.open(topbar_path) as _tb:
                        topbar = _tb.copy()

                if topbar:
                    # Resize topbar to match raid screenshot width
                    ratio = img.width / topbar.width
                    new_h = int(topbar.height * ratio)
                    topbar_resized = topbar.resize((img.width, new_h), Image.LANCZOS)
                    # Stitch: server bar on top, raid screenshot below
                    combined = Image.new("RGB", (img.width, new_h + img.height))
                    combined.paste(topbar_resized, (0, 0))
                    combined.paste(img, (0, new_h))
                    combined.save(screenshot_path)
                    try:
                        os.remove(topbar_path)
                    except Exception:
                        pass
                else:
                    img.save(screenshot_path)

                self.log(f"Screenshot: {fname}", "green")
            except Exception as e:
                self.log(f"Screenshot error: {e}", "yellow")
                try:
                    img.save(screenshot_path)
                except Exception:
                    screenshot_path = None

        # Trigger file for voice bot
        try:
            with open(TRIGGER_FILE, "w") as tf:
                tf.write(datetime.datetime.now().isoformat())
        except Exception:
            pass

        # Discord - broadcast to all configured webhooks
        webhooks = self._get_webhooks()
        if webhooks:
            ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            uptime_secs = int(time.time() - self.start_time)
            uptime_str = f"{uptime_secs // 3600:02}:{(uptime_secs % 3600) // 60:02}:{uptime_secs % 60:02}"
            # Time since last raid
            time_since = ""
            if self.last_alert_time > 0 and self.session_raid_count > 1:
                diff = int(time.time() - self.last_alert_time)
                if diff < 3600:
                    time_since = f"{diff // 60}m {diff % 60}s"
                else:
                    time_since = f"{diff // 3600}h {(diff % 3600) // 60}m"
            embed = {
                "title": "🚨  GANG BASE IS BEING RAIDED",
                "description": "Get on and defend the base.",
                "color": 0xFF2200,
                "fields": [
                    {"name": "🔍 Detection Method", "value": f"`{reason}`",                                          "inline": True},
                    {"name": "🔢 Raid Count",        "value": f"`#{self.session_raid_count} this session`",          "inline": True},
                    {"name": "⏱️ Bot Uptime",        "value": f"`{uptime_str}`",                                     "inline": True},
                    {"name": "🕐 Detected At",       "value": f"<t:{int(time.time())}:F>",                           "inline": False},
                ] + ([{"name": "⏳ Since Last Raid", "value": f"`{time_since}`", "inline": True}] if time_since else []),
                "footer": {
                    "text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}  •  Stay ready  •  Cooldown: {self.cfg.get('cooldown',30)}s"
                },
                "timestamp": ts_iso,
            }
            # Add join link as a prominent field if set
            join_link = (self.cfg.get("server_join_link") or "").strip()
            # Try auto-fetch first if enabled and cookie present
            if self.cfg.get("auto_fetch_join_link", True) and self.cfg.get("join_link_enabled", True):
                uid    = (self.cfg.get("roblox_user_id") or "").strip()
                cookie = (self.cfg.get("roblox_cookie") or "").strip()
                if uid and cookie:
                    self.log("🔄 Auto-fetching current server link...", "white")
                    try:
                        fetched = fetch_roblox_presence(uid, cookie)
                        if fetched and fetched.get("join_link") and not fetched.get("error"):
                            join_link = fetched["join_link"]
                            self.log(f"   ✓ Got live server link", "green")
                        else:
                            err = (fetched or {}).get("error", "no response")
                            self.log(f"   ⚠ Auto-fetch failed ({err}), using fallback link",
                                     "yellow")
                    except Exception as e:
                        self.log(f"   ⚠ Auto-fetch error: {e}, using fallback link", "yellow")
            if join_link and self.cfg.get("join_link_enabled", True):
                # Extract placeId and gameInstanceId from the https URL so we can
                # also provide a raw roblox:// link for users whose browser doesn't
                # handle the web redirect
                import re as _re
                embed["fields"].append({
                    "name": "🎯 Join the Server",
                    "value": f"[**→ Click here to join via ALERT's profile**]({join_link})\nClick Join on their profile page to get into the same server.",
                    "inline": False,
                })
            sent = 0
            for url, desc, wh_msg in webhooks:
                ok, info, msg_id = send_discord(url, wh_msg, screenshot_path, embed=embed)
                if ok:
                    sent += 1
                    self.log(f"  → sent to {desc}", "green")
                else:
                    self.log(f"  → FAILED {desc}: {info}", "red")
                if msg_id:
                    self._session_message_ids.append(msg_id)
            self.log(f"Discord: raid alert sent to {sent}/{len(webhooks)} webhook(s)",
                     "green" if sent else "red")

            # Capture leaderboard and send as follow-up message
            if self.cfg.get("leaderboard_enabled", True):
                self.log("Capturing leaderboard...", "white")
                lb_path = self._capture_leaderboard()
                if lb_path and os.path.exists(lb_path):
                    # Save permanently
                    lb_fname = datetime.datetime.now().strftime("leaderboard_%Y%m%d_%H%M%S.png")
                    lb_save_path = os.path.join(SCREENSHOTS_DIR, lb_fname)
                    try:
                        shutil.copy2(lb_path, lb_save_path)
                        self.log(f"Leaderboard saved: {lb_fname}", "green")
                    except Exception:
                        pass
                    lb_embed = {
                        "title": "📋  Current Server List",
                        "description": "Everyone on the server at the time of the raid.",
                        "color": 0x5865F2,
                        "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}"},
                        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                    for url, desc, _ in webhooks:
                        ok2, info2, msg_id2 = send_discord(url, None, lb_path, embed=lb_embed, filename="leaderboard.png")
                        if msg_id2:
                            self._session_message_ids.append(msg_id2)
                    self.log(f"Leaderboard: {'sent' if ok2 else 'FAILED - ' + info2}",
                             "green" if ok2 else "yellow")
                    try:
                        os.remove(lb_path)
                    except Exception:
                        pass
                else:
                    self.log("Leaderboard not captured.", "yellow")
            else:
                self.log("Leaderboard capture skipped (disabled in settings).", "white")

        if self.cfg["sound_enabled"]:
            play_sound(self.cfg.get("sound_style", "beep"))

        # Mobile push notification
        if self.cfg.get("ntfy_enabled") and self.cfg.get("ntfy_channel"):
            def _push():
                send_ntfy(self.cfg["ntfy_channel"],
                          "🚨 Gang Base Raided",
                          f"Raid #{self.session_raid_count} detected - {reason}")
            threading.Thread(target=_push, daemon=True).start()

    def _heartbeat_loop(self):
        """Send a status message to Discord immediately, then every 15 minutes."""
        while self.running:
            self._send_heartbeat()
            for _ in range(15 * 60):
                if not self.running:
                    return
                time.sleep(1)

    def _capture_topbar(self):
        """Capture the in-game info strip (server name, region, version) from the Roblox window."""
        if not self.selected_handle:
            return None
        try:
            rect = get_window_rect(self.selected_handle)
            if not rect:
                return None
            l, t, r, b = rect
            # Skip the Windows title bar (~30px) and Roblox chrome buttons row (~35px)
            # The in-game info strip sits roughly from y+35 to y+100
            bar = capture_region(l, t + 35, r, t + 100)
            if bar is None:
                return None
            tmp = os.path.join(_BASE, "_topbar_tmp.png")
            bar.save(tmp)
            return tmp
        except Exception:
            return None

    def _capture_leaderboard(self):
        """
        Press Tab to open leaderboard, scroll through capturing screenshots,
        press Tab to close, stitch all captures into one tall image.
        Returns file path of stitched image or None.
        """
        if not self.selected_handle or not WIN32_AVAILABLE or not CAPTURE_AVAILABLE or not KEYBOARD_AVAILABLE:
            return None
        try:
            rect = get_window_rect(self.selected_handle)
            if not rect:
                return None
            l, t, r, b = rect
            win_w = r - l
            win_h = b - t
            # Guard against minimised/invalid window returning zero rect
            if win_w < 100 or win_h < 100:
                self.log("Leaderboard capture: window too small or minimised.", "yellow")
                return None

            # Focus the Roblox window
            win32gui.SetForegroundWindow(self.selected_handle)
            time.sleep(0.4)

            # Press Tab to open leaderboard
            keyboard.press_and_release("tab")
            time.sleep(0.6)

            lb_left  = l + int(win_w * 0.54)
            lb_top   = t + 105
            lb_right = r - 5
            lb_bot   = b - 80

            mouse_x = lb_left + (lb_right - lb_left) // 2
            mouse_y = lb_top  + int((lb_bot - lb_top) * 0.4)

            captures = []

            win32api.SetCursorPos((mouse_x, mouse_y))
            time.sleep(0.2)

            # Scroll to top
            for _ in range(15):
                win32api.mouse_event(0x0800, 0, 0, 120, 0)
                time.sleep(0.03)
            time.sleep(0.4)

            # 4 captures with scroll between each
            for i in range(4):
                shot = capture_region(lb_left, lb_top, lb_right, lb_bot)
                if shot:
                    captures.append(shot)
                if i < 3:
                    win32api.SetCursorPos((mouse_x, mouse_y))
                    time.sleep(0.1)
                    for _ in range(3):
                        win32api.mouse_event(0x0800, 0, 0, -120, 0)
                        time.sleep(0.12)
                    time.sleep(0.7)

            # Close leaderboard
            keyboard.press_and_release("tab")
            time.sleep(0.2)

            if not captures:
                return None

            header_h = 60
            processed = [captures[0]]
            for c in captures[1:]:
                cropped = c.crop((0, header_h, c.width, c.height))
                processed.append(cropped)

            total_h = sum(c.height for c in processed)
            stitched = Image.new("RGB", (processed[0].width, total_h))
            y_off = 0
            for c in processed:
                stitched.paste(c, (0, y_off))
                y_off += c.height

            tmp = os.path.join(_BASE, "_leaderboard_tmp.png")
            stitched.save(tmp)
            return tmp

        except Exception as e:
            self.log(f"Leaderboard capture error: {e}", "yellow")
            try:
                keyboard.press_and_release("tab")
            except Exception:
                pass
            return None

    def _send_heartbeat(self):
        webhook = self.cfg.get("webhook_url", "")
        if not webhook:
            return

        # UK time - accounts for GMT/BST automatically
        # BST (UTC+1) runs last Sunday March → last Sunday October
        now_utc = datetime.datetime.now(timezone.utc)
        # Simple BST check: month 4-10 inclusive = BST, else GMT
        month = now_utc.month
        if 4 <= month <= 10:
            uk_offset = timedelta(hours=1)
            tz_label = "BST"
        else:
            uk_offset = timedelta(hours=0)
            tz_label = "GMT"
        uk_time = now_utc + uk_offset
        time_str = uk_time.strftime("%H:%M") + f" {tz_label}"
        hour = uk_time.hour

        if 6 <= hour < 12:
            watch_type = "☀️ Morning Watch"
            flavour = "Up early keeping the base safe."
        elif 12 <= hour < 18:
            watch_type = "🌤️ Day Surveillance"
            flavour = "Monitoring all activity on the gang base."
        elif 18 <= hour < 23:
            watch_type = "🌆 Evening Watch"
            flavour = "Staying alert as the night rolls in."
        else:
            watch_type = "🌙 Night Watch"
            flavour = "Running silent in the dark. Base is being watched."

        ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        uptime_secs = int(time.time() - self.start_time) if hasattr(self, "start_time") else 0
        uptime_str = f"{uptime_secs // 3600:02}:{(uptime_secs % 3600) // 60:02}:{uptime_secs % 60:02}"
        raids_today = len([e for e in self.history
                           if e.get("time","").startswith(datetime.date.today().strftime("%Y-%m-%d"))])
        embed = {
            "title": watch_type,
            "description": f"🟢 Raid bot is **online** and watching the gang base.\n*{flavour}*",
            "color": 0x3CE066,
            "fields": [
                {"name": "🕐 UK Time",      "value": f"`{time_str}`",                                        "inline": True},
                {"name": "📅 Date",         "value": f"`{uk_time.strftime('%d/%m/%Y')}`",                   "inline": True},
                {"name": "⏱️ Uptime",       "value": f"`{uptime_str}`",                                     "inline": True},
                {"name": "📋 Raids Today",  "value": f"`{raids_today}`",                                    "inline": True},
            ],
            "footer": {
                "text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}  •  Next update in 15 mins"
            },
            "timestamp": ts_iso,
        }

        # Capture top bar of Roblox window to show server/region
        topbar_path = self._capture_topbar()
        if topbar_path:
            embed["image"] = {"url": "attachment://topbar.png"}

        ok, info, msg_id = send_discord(webhook, None, screenshot_path=topbar_path, embed=embed, filename="topbar.png")
        if msg_id:
            self._session_message_ids.append(msg_id)
        self.log(f"Heartbeat sent ({watch_type}): {'OK' if ok else info}",
                 "green" if ok else "yellow")

        # Clean up temp file
        if topbar_path and os.path.exists(topbar_path):
            try:
                os.remove(topbar_path)
            except Exception:
                pass

    def _uptime_milestone_loop(self):
        """Post milestone embeds at 1h, 6h, 12h, 24h of continuous uptime."""
        milestones = [
            (1  * 3600, "⏱️ 1 Hour Online",   "The bot has been watching for 1 hour straight."),
            (6  * 3600, "⏱️ 6 Hours Online",  "Six hours of uninterrupted watch. Staying vigilant."),
            (12 * 3600, "⏱️ 12 Hours Online", "Half a day of continuous protection on the base."),
            (24 * 3600, "⏱️ 24 Hours Online", "A full day online. The base has been watched around the clock."),
        ]
        fired = set()
        while self.running:
            time.sleep(30)
            if not hasattr(self, "start_time"):
                continue
            uptime = time.time() - self.start_time
            webhook = self.cfg.get("webhook_url", "")
            if not webhook:
                continue
            for secs, title, desc in milestones:
                if uptime >= secs and secs not in fired:
                    fired.add(secs)
                    ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                    embed = {
                        "title": title,
                        "description": desc,
                        "color": 0x5865F2,
                        "fields": [
                            {"name": "🔢 Raids Detected", "value": f"`{self.session_raid_count}`", "inline": True},
                        ],
                        "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}"},
                        "timestamp": ts_iso,
                    }
                    _, _, msg_id = send_discord(webhook, None, embed=embed)
                    if msg_id:
                        self._session_message_ids.append(msg_id)
                    self.log(f"Milestone: {title}", "green")

    def _daily_summary_loop(self):
        """At 8am UK time, send a daily raid summary. Runs independently of session state."""
        while self.running:
            now_utc = datetime.datetime.now(timezone.utc)
            uk_offset = timedelta(hours=1) if 4 <= now_utc.month <= 10 else timedelta(hours=0)
            uk_now = now_utc + uk_offset
            # Calculate seconds until next 8am UK
            next_8am = uk_now.replace(hour=8, minute=0, second=0, microsecond=0)
            if uk_now >= next_8am:
                next_8am += timedelta(days=1)
            secs_until = int((next_8am - uk_now).total_seconds())
            for _ in range(secs_until):
                if not self.running:
                    return
                time.sleep(1)
            if not self.running:
                return
            if self.cfg.get("daily_summary_enabled"):
                self._send_daily_summary()

    def _send_daily_summary(self):
        webhook = self.cfg.get("webhook_url", "")
        if not webhook:
            return
        # Read fresh from history file - works even if bot was stopped overnight
        history = load_history()
        yesterday = (datetime.date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_display = (datetime.date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
        yesterday_raids = [e for e in history if e.get("time", "").startswith(yesterday)]
        count = len(yesterday_raids)
        times = [e["time"][11:16] for e in yesterday_raids]
        time_list = ", ".join(times) if times else "None"
        ts_iso = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        embed = {
            "title": f"📊 Daily Raid Summary - {yesterday_display}",
            "description": "Here's how yesterday looked on the gang base.",
            "color": 0xF0C040,
            "fields": [
                {"name": "Total Raids", "value": str(count),   "inline": True},
                {"name": "Times (UK)",  "value": time_list,    "inline": False},
            ],
            "footer": {"text": f"TYPE://KAISERS Raid Utility v{APP_VERSION}"},
            "timestamp": ts_iso,
        }
        send_discord(webhook, None, embed=embed)
        self.log(f"Daily summary sent: {count} raids on {yesterday_display}", "green")

    def _anti_afk_loop(self):
        """Click inside the Roblox window periodically to prevent AFK kick."""
        while self.running:
            interval = self.cfg.get("anti_afk_interval", 300)
            for _ in range(interval):
                if not self.running:
                    return
                time.sleep(1)
            if not self.running:
                return
            if not self.cfg.get("anti_afk_enabled") or self.paused:
                continue
            if not self.selected_handle or not WIN32_AVAILABLE:
                continue
            try:
                rect = get_window_rect(self.selected_handle)
                if not rect:
                    continue
                l, t, r, b = rect
                if (r - l) < 100 or (b - t) < 100:
                    continue
                # Click in the centre of the window
                cx = l + (r - l) // 2
                cy = t + (b - t) // 2
                # Save current cursor position
                old_pos = win32api.GetCursorPos()
                win32api.SetCursorPos((cx, cy))
                time.sleep(0.05)
                win32api.mouse_event(0x0002, 0, 0, 0, 0)  # left down
                time.sleep(0.05)
                win32api.mouse_event(0x0004, 0, 0, 0, 0)  # left up
                time.sleep(0.05)
                # Restore cursor position
                win32api.SetCursorPos(old_pos)
                self.log("Anti-AFK click sent.", "white")
            except Exception as e:
                self.log(f"Anti-AFK error: {e}", "yellow")

    def _auto_refresh_loop(self):
        """Auto-refresh window list every 30 seconds while running."""
        if not self.running:
            return
        self._refresh_windows()
        self.root.after(30000, self._auto_refresh_loop)

    def _flash_taskbar(self):
        if not self.cfg.get("flash_taskbar", True):
            return
        if WIN32_AVAILABLE:
            try:
                hwnd = self.root.winfo_id()
                ctypes.windll.user32.FlashWindow(hwnd, True)
            except Exception:
                pass

    def _animate_watch(self, tick):
        if not self.running:
            return
        messages = [
            "Watching for raids...",
            "Scanning the gang base...",
            "Eyes on the base...",
            "All quiet so far...",
            "Standing by...",
        ]
        dots = ["⬤", "◉", "⬤", "◉"]
        dot_colours = [GREEN, "#2a9e48", GREEN, "#2a9e48"]
        self.watch_dot.config(text=dots[tick % 4], fg=dot_colours[tick % 4])
        self.watch_lbl.config(text=messages[(tick // 4) % len(messages)], fg=GREEN)
        interval = self.cfg.get("scan_interval", 1)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.watch_scan_lbl.config(text=f"Last scan: {ts}  |  every {interval}s", fg=SUB)
        self.root.after(500, lambda: self._animate_watch(tick + 1))

    def _animate_raid(self):
        """Flash the status banner red briefly when a raid fires."""
        def _flash(n):
            if n <= 0:
                self.watch_dot.config(fg=GREEN)
                self.watch_lbl.config(text="Watching for raids...", fg=GREEN)
                return
            colour = ACCENT if n % 2 == 0 else YELLOW
            self.watch_dot.config(fg=colour)
            self.watch_lbl.config(text="🚨  RAID DETECTED!  🚨", fg=colour)
            self.root.after(300, lambda: _flash(n - 1))
        _flash(8)



    def _update_preview(self, img):
        try:
            # Maintain aspect ratio - fit inside 420x220
            max_w, max_h = 420, 220
            ratio = min(max_w / img.width, max_h / img.height)
            new_w = int(img.width * ratio)
            new_h = int(img.height * ratio)
            thumb = img.resize((new_w, new_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumb)
            self.preview_lbl.config(image=photo, text="", width=new_w, height=new_h)
            self.preview_lbl._img = photo
        except Exception:
            pass

    def _update_cooldown_bar(self):
        if not self.running:
            return
        elapsed = time.time() - self.last_alert_time
        cooldown = self.cfg["cooldown"]
        if elapsed >= cooldown:
            self.cd_bar["value"] = 100
            self.cd_label.config(text="Ready", fg=GREEN)
        else:
            self.cd_bar["value"] = int((elapsed / cooldown) * 100)
            self.cd_label.config(text=f"{int(cooldown-elapsed)}s", fg=YELLOW)
        self.root.after(500, self._update_cooldown_bar)

    def _update_uptime(self):
        if self.running:
            elapsed = int(time.time() - self.start_time)
            m, s = divmod(elapsed, 60)
            self.stat_uptime.config(text=f"{m:02d}:{s:02d}")
            self.root.after(1000, self._update_uptime)

    def log(self, msg, colour="white"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        def _w():
            self.log_box.config(state="normal")
            # Trim to 500 lines
            lines = int(self.log_box.index("end-1c").split(".")[0])
            if lines > 500:
                self.log_box.delete("1.0", f"{lines-500}.0")
            self.log_box.insert("end", line, colour)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.root.after(0, _w)


if __name__ == "__main__":
    root = tk.Tk()
    RaidBotApp(root)
    root.mainloop()
