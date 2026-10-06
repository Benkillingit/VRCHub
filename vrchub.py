#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VRCHub 3.0 — one app for your VRChat toolkit.
Single-file, stdlib-only Python. Windows-focused, works on Linux/macOS.

Feature union of VRCX + VRCNext + VRC-NEXUS + VRCOSC + MagicChatbox:

  Chatbox (VRCOSC / MagicChatbox / VRC-NEXUS):
    - Send text to VRChat via OSC, typing indicator
    - Quick replies, loop message, cycle lines (one per interval)
  VRChat API (VRCX / VRCNext / VRC-NEXUS):
    - Login (username/password + TOTP 2FA), session saved locally
    - Online friends list with status + world
    - My avatars: list + one-click equip (hot-swap)
    - Public avatar search + equip (VRC-NEXUS feature)
  Avatar Params (VRCOSC):
    - Any parameter by name (bool/int/float), gesture quick-fire, inputs
  Media & Chat (MagicChatbox / VRCOSC / VRC-NEXUS):
    - Show active window / Spotify track in chatbox
    - Twitch chat relay (anonymous read) -> chatbox
    - HypeRate heart rate (WebSocket) -> chatbox
  Launcher (VRCNext):
    - Launch VRChat / VRCX / VRCOSC / MagicChatbox from one place, autodetect
  AI Chat (Bas44 NPC project):
    - Talk to the ghost, optionally speak replies into VRChat

Usage:
    python3 vrchub.py
"""

import base64
import hashlib
import hmac
import json
import os
import random
import re
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

APP_NAME = "VRCHub"
APP_VERSION = "3.2.0"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vrchub_config.json")


# ================================================================ OSC engine

class OSCEngine:
    """Minimal OSC 1.0 encoder/sender (stdlib only)."""

    def __init__(self, host="127.0.0.1", port=9000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @staticmethod
    def _pad(b):
        pad = 4 - (len(b) % 4)
        return b + b"\x00" * (pad if pad else 4)

    @staticmethod
    def _encode_arg(value):
        if isinstance(value, bool):
            return ("T" if value else "F"), b""
        if isinstance(value, int):
            return "i", struct.pack(">i", value)
        if isinstance(value, float):
            return "f", struct.pack(">f", value)
        if isinstance(value, str):
            return "s", OSCEngine._pad(value.encode("utf-8"))
        raise TypeError("Unsupported OSC arg type: %r" % type(value))

    def send(self, address, *args):
        typetags = "".join(t for t, _ in (self._encode_arg(a) for a in args))
        payload = self._pad(address.encode("utf-8"))
        payload += self._pad(("," + typetags).encode("utf-8"))
        for a in args:
            payload += self._encode_arg(a)[1]
        self.sock.sendto(payload, (self.host, self.port))

    def chatbox(self, text, send_immediately=True, notify=False):
        if not text.strip():
            return False
        self.send("/chatbox/input", text, send_immediately, notify)
        return True

    def typing(self, on=True):
        self.send("/chatbox/typing", bool(on))

    def avatar_param(self, name, value):
        self.send("/avatar/parameters/" + name, value)

    def input_jump(self, hold=True):
        self.send("/input/Jump", 1 if hold else 0)

    def input_look(self, x=0.0, y=0.0):
        self.send("/input/LookHorizontal", float(x))
        self.send("/input/LookVertical", float(y))


# ================================================================ TOTP (2FA)

def totp_code(secret, t=None, period=30):
    """RFC 6238 TOTP from a base32 secret (stdlib only)."""
    s = secret.replace(" ", "").upper()
    s = s + "=" * ((8 - len(s) % 8) % 8)
    key = base64.b32decode(s, casefold=True)
    counter = struct.pack(">Q", int((t if t is not None else time.time()) // period))
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    o = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[o:o + 4])[0] & 0x7FFFFFFF) % 1000000
    return str(code).zfill(6)


# ================================================================ VRChat API

class VRChatAPI:
    """VRChat web API client (VRCX-style): login, friends, avatars, equip."""

    BASE = "https://api.vrchat.com/api/1"
    UA = "VRCHub/2.0 (github.com/Benkillingit/VRCHub)"

    class Needs2FA(Exception):
        pass

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))

    # ---- plumbing

    def _request(self, method, path, data=None, basic=None, raw=False):
        url = self.BASE + path
        headers = {"User-Agent": self.UA}
        body = None
        if basic is not None:
            tok = base64.b64encode(
                ("%s:%s" % basic).encode("utf-8")).decode("ascii")
            headers["Authorization"] = "Basic " + tok
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=25) as resp:
                text = resp.read().decode("utf-8", "replace")
                return resp.status, text
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    @staticmethod
    def _json(text):
        try:
            return json.loads(text)
        except ValueError:
            return {"error": {"message": text[:200]}}

    # ---- auth

    def login(self, username, password, totp=None):
        status, text = self._request("GET", "/auth/user", basic=(username, password))
        data = self._json(text)
        needs2fa = ("twoFactor" in str(data)[:400].lower()
                    or "2 factor" in str(data)[:400].lower())
        if needs2fa:
            if not totp:
                raise self.Needs2FA("Enter your 6-digit 2FA code")
            s2, t2 = self._request("POST", "/auth/twofactorauth/totp/verify",
                                    data={"code": totp})
            if s2 not in (200, 201):
                raise RuntimeError("2FA failed: " + str(self._json(t2).get(
                    "error", {}).get("message", t2[:120])))
            status, text = self._request("GET", "/auth/user")
        if status not in (200, 201):
            raise RuntimeError("Login failed: " + str(
                self._json(text).get("error", {}).get("message", text[:120])))
        return self._json(text)

    def cookies(self):
        return {c.name: c.value for c in self.jar}

    def load_cookies(self, cookies):
        """Restore a saved session (auth + twoFactorAuth cookies)."""
        for name, val in (cookies or {}).items():
            self.jar.set_cookie(http.cookiejar.Cookie(
                version=0, name=name, value=val, port=None, port_specified=False,
                domain=".vrchat.com", domain_specified=True, domain_initial_dot=True,
                path="/", path_specified=True, secure=True, expires=None,
                discard=False, comment=None, comment_url=None,
                rest={}, rfc2109=False))

    def me(self):
        status, text = self._request("GET", "/auth/user")
        if status != 200:
            raise RuntimeError("Session invalid — log in again.")
        return self._json(text)

    # ---- features

    def friends_online(self, include_offline=False):
        status, text = self._request(
            "GET", "/friends?offline=%s&n=100&order=last_login"
            % ("true" if include_offline else "false"))
        if status != 200:
            raise RuntimeError("Could not load friends: " + text[:120])
        out = []
        for f in self._json(text):
            out.append({
                "id": f.get("id", ""),
                "name": f.get("displayName", "?"),
                "status": f.get("status", "?"),
                "state": f.get("state", "?"),
                "world": f.get("location", "offline"),
            })
        return out

    def my_avatars(self):
        q = "/avatars?user=me&releaseStatus=all&n=60&order=updated"
        status, text = self._request("GET", q)
        if status != 200:
            raise RuntimeError("Could not load avatars: " + text[:120])
        out = []
        for a in self._json(text):
            out.append({"id": a.get("id"), "name": a.get("name", "?"),
                        "author": a.get("authorName", ""),
                        "desc": (a.get("description") or "")[:80]})
        return out

    def search_public_avatars(self, query):
        q = "/avatars?search=" + urllib.parse.quote(query) + "&n=20"
        status, text = self._request("GET", q)
        if status != 200:
            raise RuntimeError("Search failed: " + text[:120])
        return [{"id": a.get("id"), "name": a.get("name", "?"),
                 "author": a.get("authorName", "?"),
                 "desc": (a.get("description") or "")[:80]}
                for a in self._json(text)]

    def search_worlds(self, query):
        q = "/worlds?search=" + urllib.parse.quote(query) + "&n=20"
        status, text = self._request("GET", q)
        if status != 200:
            raise RuntimeError("World search failed: " + text[:120])
        return [{"id": w.get("id"), "name": w.get("name", "?"),
                 "author": w.get("authorName", "?"),
                 "occupants": w.get("occupants", 0)}
                for w in self._json(text)]

    def world_instances(self, world_id):
        status, text = self._request("GET", "/worlds/%s"
                                    % urllib.parse.quote(world_id))
        if status != 200:
            raise RuntimeError("World lookup failed: " + text[:120])
        d = self._json(text)
        out = []
        for ins in d.get("instances", []):
            if isinstance(ins, (list, tuple)) and ins:
                occ = 0
                if len(ins) > 1:
                    if isinstance(ins[1], (int, float)):
                        occ = int(ins[1])
                    elif isinstance(ins[1], dict):
                        for k in ("count", "occupantCount", "occupants"):
                            if isinstance(ins[1].get(k), (int, float)):
                                occ = int(ins[1][k])
                                break
                out.append({"location": ins[0], "occupants": occ})
            elif isinstance(ins, dict):
                out.append({"location": ins.get("location", "?"),
                            "occupants": ins.get("occupantCount", 0)})
        return d.get("name", "?"), d.get("id", world_id), out

    def notifications(self):
        status, text = self._request(
            "GET", "/auth/user/notifications?n=20")
        if status != 200:
            raise RuntimeError("Notifications failed: " + text[:120])
        out = []
        for n in self._json(text):
            out.append({"id": n.get("id"),
                        "type": n.get("type", "?"),
                        "sender": (n.get("senderUserId") or "?"),
                        "title": n.get("title", ""),
                        "detail": json.dumps(n.get("details", {}))[:100]})
        return out

    def respond_notification(self, notif_id, accept=True):
        action = "accept" if accept else "hide"
        status, text = self._request(
            "PUT", "/auth/user/notifications/%s/%s"
            % (urllib.parse.quote(notif_id), action))
        if status not in (200, 201):
            raise RuntimeError("Notification %s failed: " % action + text[:120])

    def block_user(self, user_id, block=True):
        action = "PUT" if block else "DELETE"
        status, text = self._request(
            action, "/auth/user/blocks/%s" % urllib.parse.quote(user_id))
        if status not in (200, 201, 204):
            raise RuntimeError("Block failed: " + text[:120])

    def mute_user(self, user_id, mute=True):
        action = "PUT" if mute else "DELETE"
        status, text = self._request(
            action, "/auth/user/mute/%s" % urllib.parse.quote(user_id))
        if status not in (200, 201, 204):
            raise RuntimeError("Mute failed: " + text[:120])

    def avatar_favorites(self, limit=30):
        """Favorite avatars with names (VRCX favorite bar)."""
        status, text = self._request("GET", "/favorites?type=favorite&n=100")
        if status != 200:
            raise RuntimeError("Favorites failed: " + text[:120])
        favs = self._json(text)
        out = []
        for f in favs:
            favid = f.get("favoriteId", "")
            if not favid.startswith("avtr_"):
                continue
            s2, t2 = self._request("GET", "/avatars/%s"
                                   % urllib.parse.quote(favid))
            name = favid
            if s2 == 200:
                name = self._json(t2).get("name", favid)
            out.append({"id": favid, "name": name,
                        "group": f.get("favoriteGroupId", "")})
            if len(out) >= limit:
                break
        return out

    def equip_avatar(self, avatar_id):
        status, text = self._request(
            "PUT", "/avatars/%s/select" % urllib.parse.quote(avatar_id), data={})
        if status not in (200, 201):
            raise RuntimeError("Equip failed: " + str(
                self._json(text).get("error", {}).get("message", text[:120])))
        return self._json(text)


# ================================================================ Twitch IRC

class TwitchIRC:
    """Anonymous read-only Twitch chat over plain IRC (stdlib only)."""

    HOST = "irc.chat.twitch.tv"
    PORT = 6667

    def __init__(self, on_message=None, on_status=None):
        self.on_message = on_message or (lambda u, m: None)
        self.on_status = on_status or (lambda s: None)
        self.sock = None
        self.running = False
        self.channel = None

    def connect(self, channel):
        self.channel = channel if channel.startswith("#") else "#" + channel
        self.sock = socket.create_connection((self.HOST, self.PORT), timeout=15)
        nick = "justinfan%05d" % random.randint(0, 99999)
        self.sock.sendall(("NICK %s\r\n" % nick).encode("utf-8"))
        self.sock.sendall(("JOIN %s\r\n" % self.channel).encode("utf-8"))
        self.running = True
        self.on_status("Connected to %s" % self.channel)
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self):
        buf = b""
        try:
            while self.running:
                buf += self.sock.recv(4096)
                while b"\r\n" in buf:
                    line, buf = buf.split(b"\r\n", 1)
                    self._handle(line.decode("utf-8", "replace"))
        except OSError:
            pass
        if self.running:
            self.on_status("Disconnected from Twitch")
            self.running = False

    def _handle(self, line):
        m = re.match(r":(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.*)", line)
        if m:
            self.on_message(m.group(1), m.group(2))

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass


# ================================================================ WebSocket (HypeRate)

class WSClient:
    """Tiny masked-frame WebSocket client (ws:// and wss://, stdlib only)."""

    def __init__(self, url):
        m = re.match(r"wss?://([^/]+)(/.*)?$", url)
        self.secure = url.startswith("wss")
        hostport = m.group(1)
        if ":" in hostport and not hostport.startswith("["):
            self.host, self.port = hostport.rsplit(":", 1)
            self.port = int(self.port)
        else:
            self.host, self.port = hostport, (443 if self.secure else 80)
        self.path = m.group(2) or "/"
        self.sock = None

    def connect(self):
        raw = socket.create_connection((self.host, self.port), timeout=15)
        if self.secure:
            ctx = ssl.create_default_context()
            self.sock = ctx.wrap_socket(raw, server_hostname=self.host)
        else:
            self.sock = raw
        key = base64.b64encode(os.urandom(16)).decode()
        hosthdr = self.host if ((self.secure and self.port == 443) or
                                (not self.secure and self.port == 80)) \
            else "%s:%d" % (self.host, self.port)
        req = ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
               "Sec-WebSocket-Version: 13\r\n\r\n" % (self.path, hosthdr, key))
        self.sock.sendall(req.encode("utf-8"))
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise OSError("WS handshake failed")
            resp += chunk
        if b"101" not in resp.split(b"\r\n")[0]:
            raise OSError("WS handshake rejected: %s" % resp[:80])

    def send(self, text):
        data = text.encode("utf-8")
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        hdr = b"\x81"
        n = len(data)
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.sock.sendall(hdr + mask + masked)

    def recv(self, timeout=10):
        self.sock.settimeout(timeout)

        def _exact(n):
            b = b""
            while len(b) < n:
                c = self.sock.recv(n - len(b))
                if not c:
                    raise OSError("WS closed")
                b += c
            return b

        while True:
            b1, b2 = _exact(2)
            opcode = b1 & 0x0F
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", _exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", _exact(8))[0]
            if b2 & 0x80:  # server frames are unmasked, but be safe
                _exact(4)
            payload = _exact(length) if length else b""
            if opcode == 0x9:  # ping -> pong (echo payload, masked)
                mask = os.urandom(4)
                masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                n = len(payload)
                if n < 126:
                    hdr = b"\x8a" + bytes([0x80 | n])
                else:
                    hdr = b"\x8a" + bytes([0x80 | 126]) + struct.pack(">H", n)
                self.sock.sendall(hdr + mask + masked)
                continue
            if opcode == 0x8:
                raise OSError("WS closed by server")
            return payload.decode("utf-8", "replace")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ================================================================ OSC listener

class OSCDecoder:
    """Decode an OSC 1.0 packet into (address, [args])."""

    @staticmethod
    def decode(data):
        # address
        end = data.index(b"\x00")
        address = data[:end].decode("utf-8", "replace")
        rest = data[end + 1:]
        # skip padding to 4
        rest = rest[(4 - len(data[:end + 1]) % 4) % 4:]
        # typetags
        if not rest or rest[:1] != b",":
            return address, []
        t_end = rest.index(b"\x00")
        tags = rest[1:t_end].decode("ascii", "replace")
        body = rest[t_end + 1:]
        body = body[(4 - (t_end + 1) % 4) % 4:]
        args = []
        for t in tags:
            if t == "i":
                args.append(struct.unpack(">i", body[:4])[0]); body = body[4:]
            elif t == "f":
                args.append(struct.unpack(">f", body[:4])[0]); body = body[4:]
            elif t == "s":
                s_end = body.index(b"\x00")
                args.append(body[:s_end].decode("utf-8", "replace"))
                taken = s_end + 1
                body = body[taken + ((4 - taken % 4) % 4):]
            elif t == "T":
                args.append(True)
            elif t == "F":
                args.append(False)
        return address, args


class OSCListener:
    """UDP listener for outbound OSC events from VRChat / VRCX / VRCOSC / MCB."""

    def __init__(self, host="127.0.0.1", port=9001, on_event=None):
        self.host, self.port = host, port
        self.on_event = on_event or (lambda addr, args: None)
        self.sock = None
        self.running = False

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.settimeout(1)
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
                address, args = OSCDecoder.decode(data)
                self.on_event(address, args)
            except socket.timeout:
                continue
            except OSError:
                return

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass


def check_port(host, port, timeout=1.0):
    """Is something listening on this local port? (app detection)"""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except OSError:
        return False


def running_processes():
    """Names of running processes (Windows: tasklist, else ps)."""
    try:
        if sys.platform == "win32":
            out = subprocess.check_output(
                ["tasklist", "/FO", "CSV"], stderr=subprocess.DEVNULL,
                text=True, timeout=10)
            return [line.split('","')[0].strip('"').lower()
                    for line in out.splitlines()[1:] if line.strip()]
        out = subprocess.check_output(["ps", "-e"], text=True, timeout=10)
        return [l.split()[3].lower() for l in out.splitlines()[1:] if len(l.split()) > 3]
    except Exception:
        return []


HYPHERATE_WS = "wss://app.hypereact.com/ws"


# ================================================================ AI engine

AI_ENDPOINT = "https://superagent-d511f44c.base44.app/functions/vrcNpcReply"
AI_FALLBACK_REPLY = ("My ghost brain is offline right now. "
                     "(AI endpoint unreachable — try again later.)")


def ask_ai(question, user="VRCHub"):
    try:
        url = (AI_ENDPOINT + "?q=" + urllib.parse.quote(question) +
               "&u=" + urllib.parse.quote(user))
        req = urllib.request.Request(
            url, headers={"User-Agent": "VRCHub/" + APP_VERSION})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace").strip()
        return body or AI_FALLBACK_REPLY
    except Exception as e:
        return AI_FALLBACK_REPLY + " [%s]" % e.__class__.__name__


# ================================================================ config

DEFAULT_TOOLS = {
    "VRChat":       ["vrchat.exe", ["vrchat"]],
    "VRCX":         ["VRCX.exe", ["vrcx"]],
    "VRCOSC":       ["VRCOSC.exe", ["vrcosc"]],
    "MagicChatbox": ["MagicChatbox.exe", ["magicchatbox"]],
}


def load_config():
    cfg = {
        "osc_host": "127.0.0.1",
        "osc_port": 9000,
        "ai_to_chatbox": True,
        "tools": {},
        "user_name": "Ben",
        "quick_replies": [
            "Hello!", "Nice avatar!", "How's everyone doing?",
            "BRB one sec", "That's hilarious", "Take care o/",
        ],
        "vrchat_cookies": {},
        "profiles": {},
        "wear_times": {},
        "avatar_memos": {},
    }
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            cfg.update(loaded)
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def autodetect(tools):
    roots = [
        os.path.expandvars(r"%ProgramFiles%"),
        os.path.expandvars(r"%ProgramFiles(x86)%"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%APPDATA%"),
        os.path.expanduser(r"~\Desktop"),
        os.path.expanduser(r"~\Downloads"),
        r"C:\Program Files",
        r"C:\Program Files (x86)",
    ]
    found = {}
    if sys.platform != "win32":
        return found
    for label, (_exe, hints) in tools.items():
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                depth = dirpath[len(root):].count(os.sep)
                if depth >= 3:
                    dirnames[:] = []
                    continue
                for fn in filenames:
                    low = fn.lower()
                    if low.endswith(".exe") and any(h in low for h in hints):
                        found[label] = os.path.join(dirpath, fn)
                        break
                if label in found:
                    break
            if label in found:
                break
    return found


# ================================================================ window titles

def get_window_titles(limit=30):
    """Visible window titles on Windows (MagicChatbox-style media detection)."""
    titles = []
    if sys.platform != "win32":
        return titles
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.SetArgTypes = None
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def foreach(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if 0 < length < 120:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    t = buf.value.strip()
                    if t and t != "Program Manager":
                        titles.append(t)
            return True

        user32.EnumWindows(EnumWindowsProc(foreach), 0)
    except Exception:
        pass
    return titles[:limit]


def spotify_title(titles):
    """Best-effort current-track extraction from window titles."""
    for t in titles:
        if "Spotify" in t and t not in ("Spotify", "Spotify Free",
                                       "Spotify Premium"):
            return t
    return None


# ================================================================ GUI

# ================================================================ system info

def battery_percent():
    """Battery % on Windows via GetSystemPowerStatus (0/None if absent)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_ubyte),
                        ("BatteryFlag", ctypes.c_ubyte),
                        ("BatteryLifePercent", ctypes.c_ubyte),
                        ("Reserved1", ctypes.c_ubyte),
                        ("BatteryLifeTime", ctypes.c_ulong),
                        ("BatteryFullLifeTime", ctypes.c_ulong)]
        sps = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
            p = sps.BatteryLifePercent
            return p if p != 255 else None
    except Exception:
        pass
    return None


def ram_usage():
    """(used_gb, total_gb) on Windows via GlobalMemoryStatusEx."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            total = m.ullTotalPhys / (1024 ** 3)
            used = (m.ullTotalPhys - m.ullAvailPhys) / (1024 ** 3)
            return round(used, 1), round(total, 1)
    except Exception:
        pass
    return None


GESTURES = ["Neutral", "Fist", "Open", "Point", "Peace", "RockNRoll",
            "Gun", "ThumbsUp"]


class VRCHubApp(tk.Tk):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.osc = OSCEngine(cfg["osc_host"], int(cfg["osc_port"]))
        _base_send = self.osc.send

        def _hooked_send(address, *args):
            self.last_activity = time.time()
            if self.afk_running and self._afk_sent and \
                    address != "/chatbox/input":
                self._afk_sent = False
            return _base_send(address, *args)

        self.osc.send = _hooked_send
        self.api = VRChatAPI()
        self.twitch = None
        self.hr_ws = None
        self.hr_running = False
        self.vrcx_ws = None
        self.vrcx_running = False
        self.osc_listener = None
        self.osc_listening = False
        self.last_activity = time.time()
        self.pul_running = False
        self.pul_ws = None
        self._wear_start = None
        self.friend_watch_running = False
        self._friend_states = {}
        self.afk_running = False
        self.watch_running = False
        self.gcycle_running = False
        self.sysstat_running = False
        self._afk_sent = False
        self.cycle_running = False
        self.media_running = False
        self._loop_running = False
        self.title("%s %s — your VRChat toolkit in one place"
                   % (APP_NAME, APP_VERSION))
        self.geometry("840x600")
        self.minsize(720, 520)
        self._build_ui()
        self._try_session()

    # ---- shared

    def status(self, msg):
        self.status_var.set(msg)
        self.after(6000, lambda: self.status_var.set("Ready."))

    def _send_chatbox(self, text):
        if self.osc.chatbox(text):
            self.status('Sent: "%s"' % text[:40])
        else:
            self.status("Empty message, not sent.")

    def _build_ui(self):
        self.status_var = tk.StringVar(value="Ready.")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        self._tab_chatbox(nb)
        self._tab_ai(nb)
        self._tab_api(nb)
        self._tab_params(nb)
        self._tab_media(nb)
        self._tab_worlds(nb)
        self._tab_extras(nb)
        self._tab_connect(nb)
        self._tab_tools(nb)
        sb = ttk.Frame(self)
        sb.pack(fill="x", side="bottom")
        ttk.Label(sb, textvariable=self.status_var, anchor="w",
                  padding=(8, 2)).pack(side="left")
        ttk.Label(sb, text="OSC %s:%d  |  stdlib-only  |  MIT  |  v%s"
                  % (self.osc.host, self.osc.port, APP_VERSION),
                  anchor="e", padding=(8, 2)).pack(side="right")

    # ---- Chatbox tab (VRCOSC / MCB / Nexus)

    def _tab_chatbox(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Chatbox  ")

        ttk.Label(f, text="Send text to the VRChat chatbox. Enable OSC in "
                          "VRChat: Settings → OSC → ON (port 9000).").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.chat_entry = ttk.Entry(f, font=("Segoe UI", 13))
        self.chat_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        self.chat_entry.bind("<Return>", lambda e: self._send_from_entry())
        self.chat_entry.bind("<KeyRelease>", self._on_typing)
        ttk.Button(f, text="Send", command=self._send_from_entry).grid(
            row=1, column=2, padx=(6, 0))

        self.typing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Send typing indicator while typing",
                        variable=self.typing_var).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(4, 10))

        qr = ttk.LabelFrame(f, text="Quick replies", padding=6)
        qr.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        for i, msg in enumerate(self.cfg.get("quick_replies", [])):
            ttk.Button(qr, text=msg, width=18,
                       command=lambda m=msg: self._send_chatbox(m)
                       ).grid(row=i // 4, column=i % 4, padx=3, pady=3)

        # Nexus-style cycle lines
        cyc = ttk.LabelFrame(f, text="Cycle lines (VRC-NEXUS style, one per "
                                     "line)", padding=6)
        cyc.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.cycle_text = scrolledtext.ScrolledText(cyc, height=4, width=52)
        self.cycle_text.grid(row=0, column=0, columnspan=2, sticky="ew")
        side = ttk.Frame(cyc)
        side.grid(row=0, column=2, sticky="ns", padx=(8, 0))
        ttk.Label(side, text="Every (sec):").pack()
        self.cycle_secs = ttk.Spinbox(side, from_=3, to=3600, width=5, value=15)
        self.cycle_secs.pack()
        self.cycle_btn = ttk.Button(side, text="Start", command=self._toggle_cycle)
        self.cycle_btn.pack(pady=4, fill="x")

        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)
        cyc.columnconfigure(0, weight=1)

    def _send_from_entry(self):
        text = self.chat_entry.get().strip()
        if text:
            self._send_chatbox(text)
            self.chat_entry.delete(0, "end")
            if self.typing_var.get():
                self.osc.typing(False)

    def _on_typing(self, event):
        if self.typing_var.get() and event.keysym not in ("Return", "Escape"):
            self.osc.typing(bool(self.chat_entry.get()))
            self.after(1500, lambda: self.osc.typing(False))

    def _toggle_cycle(self):
        if self.cycle_running:
            self.cycle_running = False
            self.cycle_btn.config(text="Start")
            self.status("Cycle stopped.")
            return
        lines = [l.strip() for l in
                 self.cycle_text.get("1.0", "end").splitlines() if l.strip()]
        try:
            secs = max(3, int(float(self.cycle_secs.get())))
        except ValueError:
            secs = 15
        if not lines:
            self.status("Add some lines to cycle first.")
            return

        def run():
            self.cycle_running = True
            self.cycle_btn.config(text="Stop")
            i = 0
            while self.cycle_running:
                self.osc.chatbox(lines[i % len(lines)])
                i += 1
                for _ in range(secs * 10):
                    if not self.cycle_running:
                        return
                    time.sleep(0.1)

        threading.Thread(target=run, daemon=True).start()
        self.status("Cycling %d line(s) every %ds." % (len(lines), secs))

    # ---- AI tab

    def _tab_ai(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  AI Chat  ")
        ttk.Label(f, text="Talk to the Bas44 ghost. With 'relay' on, each reply "
                          "is also sent to your VRChat chatbox.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.ai_log = scrolledtext.ScrolledText(f, height=16, state="disabled",
                                                font=("Consolas", 10), wrap="word")
        self.ai_log.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=4)
        self.ai_entry = ttk.Entry(f, font=("Segoe UI", 12))
        self.ai_entry.grid(row=2, column=0, sticky="ew", pady=4)
        self.ai_entry.bind("<Return>", lambda e: self._send_ai())
        self.ai_relay = tk.BooleanVar(value=bool(self.cfg.get("ai_to_chatbox", True)))
        ttk.Checkbutton(f, text="Relay replies to chatbox",
                        variable=self.ai_relay).grid(row=3, column=0, sticky="w")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)
        self._ai_log_append("Ghost online. Ask me anything.\n")

    def _ai_log_append(self, text):
        self.ai_log.config(state="normal")
        self.ai_log.insert("end", text)
        self.ai_log.see("end")
        self.ai_log.config(state="disabled")

    def _send_ai(self):
        q = self.ai_entry.get().strip()
        if not q:
            return
        self.ai_entry.delete(0, "end")
        self._ai_log_append("You: %s\n" % q)
        threading.Thread(target=self._ai_worker, args=(q,), daemon=True).start()

    def _ai_worker(self, q):
        self.after(0, lambda: self.status("Ghost is thinking..."))
        reply = ask_ai(q, user=self.cfg.get("user_name", "VRCHub"))

        def show():
            self._ai_log_append("Ghost: %s\n\n" % reply)
            if self.ai_relay.get():
                self.osc.chatbox(reply)
            self.status("Ready.")
        self.after(0, show)

    # ---- VRChat API tab (VRCX / VRCNext / Nexus)

    def _tab_api(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  VRChat API  ")

        login = ttk.LabelFrame(f, text="Login (saved to vrchub_config.json as a "
                                      "session cookie)", padding=6)
        login.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(login, text="User:").grid(row=0, column=0)
        self.vrc_user = ttk.Entry(login, width=22)
        self.vrc_user.grid(row=0, column=1, padx=4)
        ttk.Label(login, text="Pass:").grid(row=0, column=2)
        self.vrc_pass = ttk.Entry(login, width=22, show="*")
        self.vrc_pass.grid(row=0, column=3, padx=4)
        ttk.Label(login, text="2FA:").grid(row=1, column=0)
        self.vrc_totp = ttk.Entry(login, width=22)
        self.vrc_totp.grid(row=1, column=1, padx=4, pady=2)
        ttk.Button(login, text="Login", command=self._do_login).grid(
            row=1, column=3, padx=4)
        self.vrc_me_label = ttk.Label(login, text="Not logged in.")
        self.vrc_me_label.grid(row=2, column=0, columnspan=4, sticky="w")
        prow = ttk.Frame(login)
        prow.grid(row=3, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Label(prow, text="Profile:").pack(side="left")
        self.profile_name = ttk.Entry(prow, width=12)
        self.profile_name.pack(side="left", padx=3)
        ttk.Button(prow, text="Save session", width=13,
                   command=self._save_profile).pack(side="left", padx=2)
        ttk.Button(prow, text="Load", width=6,
                   command=self._load_profile).pack(side="left", padx=2)
        ttk.Label(prow, text="(multi-account: save several, type name + Load "
                             "to switch)").pack(side="left", padx=4)
        # offline friends toggle
        self.friends_offline = tk.BooleanVar(value=False)
        ttk.Checkbutton(prow, text="Include offline",
                        variable=self.friends_offline).pack(side="right")

        # friends
        fr = ttk.LabelFrame(f, text="Online friends (VRCX-style)", padding=6)
        fr.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=4)
        cols = ("name", "status", "world")
        self.friends_tree = ttk.Treeview(fr, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (150, 90, 160)):
            self.friends_tree.heading(c, text=c.capitalize())
            self.friends_tree.column(c, width=w)
        self.friends_tree.pack(fill="both", expand=True)
        ttk.Button(fr, text="Load friends", command=self._load_friends).pack(pady=3)
        wrow = ttk.Frame(fr)
        wrow.pack(fill="x", pady=3)
        self.fwatch_btn = ttk.Button(wrow, text="Watch (chatbox alerts)",
                                     command=self._toggle_friend_watch)
        self.fwatch_btn.pack(side="left")
        for label, cmd in (
                ("Block", lambda: self._mod_friend("block")),
                ("Unblock", lambda: self._mod_friend("unblock")),
                ("Mute", lambda: self._mod_friend("mute")),
                ("Unmute", lambda: self._mod_friend("unmute"))):
            ttk.Button(wrow, text=label, width=7,
                       command=cmd).pack(side="left", padx=2)
        ttk.Label(wrow, text="select a friend first").pack(side="left", padx=4)

        # avatars
        av = ttk.LabelFrame(f, text="Avatars — equip = hot-swap (Nexus-style)",
                            padding=6)
        av.grid(row=1, column=1, sticky="nsew", pady=4)
        self.avatar_tree = ttk.Treeview(av, columns=("name", "author"),
                                        show="headings", height=8)
        self.avatar_tree.heading("name", text="Name")
        self.avatar_tree.column("name", width=170)
        self.avatar_tree.heading("author", text="Author")
        self.avatar_tree.column("author", width=120)
        self.avatar_tree.pack(fill="both", expand=True)
        ttk.Button(av, text="Load my avatars",
                   command=self._load_avatars).pack(pady=3)
        row = ttk.Frame(av)
        row.pack(fill="x", pady=3)
        self.av_search = ttk.Entry(row)
        self.av_search.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Search public", width=14,
                   command=self._search_avatars).pack(side="left", padx=4)
        ttk.Button(av, text="Equip selected", command=self._equip_avatar).pack()
        mrow = ttk.Frame(av)
        mrow.pack(fill="x", pady=(3, 0))
        ttk.Label(mrow, text="Memo:").pack(side="left")
        self.av_memo = ttk.Entry(mrow, width=24)
        self.av_memo.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(mrow, text="Save memo", width=10,
                   command=self._save_memo).pack(side="left")
        self.av_wear = ttk.Label(av, text="Wear time: select an avatar")
        self.av_wear.pack(anchor="w", pady=(2, 0))
        self.avatar_tree.bind("<<TreeviewSelect>>",
                              lambda e: self._avatar_selected())

        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=1)
        f.rowconfigure(1, weight=1)

    def _try_session(self):
        cookies = self.cfg.get("vrchat_cookies", {})
        if cookies.get("auth"):
            self.api.load_cookies(cookies)
            try:
                me = self.api.me()
                self.vrc_me_label.config(
                    text="Session restored: %s" % me.get("displayName", "?"))
            except Exception:
                self.vrc_me_label.config(text="Saved session expired — log in.")

    def _do_login(self):
        user = self.vrc_user.get().strip()
        pw = self.vrc_pass.get()
        totp = self.vrc_totp.get().strip() or None

        def work():
            try:
                me = self.api.login(user, pw, totp)
                self.cfg["vrchat_cookies"] = self.api.cookies()
                save_config(self.cfg)

                def ok():
                    self.vrc_me_label.config(
                        text="Logged in: %s (%s)" % (
                            me.get("displayName"), me.get("status")))
                    self.status("VRChat login OK.")
                self.after(0, ok)
            except VRChatAPI.Needs2FA as e:
                self.after(0, lambda: (self.vrc_me_label.config(
                    text=str(e)), self.status(str(e))))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: (self.vrc_me_label.config(text=msg),
                                       self.status(msg)))
        threading.Thread(target=work, daemon=True).start()
        self.status("Logging in to VRChat...")

    def _save_profile(self):
        name = self.profile_name.get().strip()
        if not name:
            self.status("Type a profile name first.")
            return
        cookies = self.cfg.get("vrchat_cookies") or self.api.cookies()
        self.cfg.setdefault("profiles", {})[name] = {"cookies": cookies}
        save_config(self.cfg)
        self.status("Profile '%s' saved." % name)

    def _load_profile(self):
        name = self.profile_name.get().strip()
        prof = (self.cfg.get("profiles") or {}).get(name)
        if not prof:
            self.status("No profile named '%s'." % name)
            return
        self.api = VRChatAPI()
        self.api.load_cookies(prof.get("cookies", {}))
        try:
            me = self.api.me()
            self.cfg["vrchat_cookies"] = self.api.cookies()
            save_config(self.cfg)
            self.vrc_me_label.config(
                text="Switched to '%s': %s" % (name, me.get("displayName", "?")))
            self.status("Profile switched.")
        except Exception as e:
            self.status("Profile session expired: %s" % str(e)[:60])

    def _avatar_selected(self):
        sel = self.avatar_tree.selection()
        if not sel:
            return
        av_id = sel[0]
        self.av_memo.delete(0, "end")
        self.av_memo.insert(0, (self.cfg.get("avatar_memos") or {}).get(av_id, ""))
        mins = (self.cfg.get("wear_times") or {}).get(av_id, 0)
        self.av_wear.config(text="Wear time: %dh %02dm" % (mins // 60, mins % 60))

    def _save_memo(self):
        sel = self.avatar_tree.selection()
        if not sel:
            self.status("Select an avatar first.")
            return
        self.cfg.setdefault("avatar_memos", {})[sel[0]] = \
            self.av_memo.get().strip()
        save_config(self.cfg)
        self.status("Memo saved.")

    def _note_equip(self, av_id, name):
        """Close out the previous wear interval, start a new one
        (VRCX 'avatar wear times' request, 7+ votes)."""
        now = time.time()
        if self._wear_start:
            old_id, t0 = self._wear_start
            mins = int((now - t0) // 60)
            if mins > 0:
                times = self.cfg.setdefault("wear_times", {})
                times[old_id] = times.get(old_id, 0) + mins
        self._wear_start = (av_id, now)
        save_config(self.cfg)
        self.status("Equipped '%s' — wear timer running." % name[:40])
        self._avatar_selected()

    def _toggle_friend_watch(self):
        """Alert in chatbox when a friend goes offline or moves worlds
        (VRCX 'notify when favorited friend leaves instance', 13+ votes)."""
        if self.friend_watch_running:
            self.friend_watch_running = False
            self.fwatch_btn.config(text="Watch (chatbox alerts)")
            self.status("Friend watch off.")
            return

        def run():
            self.friend_watch_running = True
            self.fwatch_btn.config(text="Watching (stop)")
            first = True
            while self.friend_watch_running:
                try:
                    friends = self.api.friends_online(include_offline=True)
                except Exception:
                    time.sleep(60)
                    continue
                now_states = {f["name"]: (f["state"], f["world"])
                              for f in friends}
                if not first:
                    for nm, (state, world) in now_states.items():
                        old = self._friend_states.get(nm)
                        if old is None:
                            continue
                        old_state, old_world = old
                        if old_state == "online" and state != "online":
                            self.osc.chatbox("%s went offline" % nm, notify=True)
                        elif old_state == "online" and state == "online" \
                                and world != old_world:
                            self.osc.chatbox("%s changed world" % nm,
                                             notify=True)
                self._friend_states = now_states
                first = False
                for _ in range(600):
                    if not self.friend_watch_running:
                        return
                    time.sleep(0.1)

        threading.Thread(target=run, daemon=True).start()
        self.status("Friend watch on (60s poll).")

    def _mod_friend(self, kind):
        sel = self.friends_tree.selection()
        if not sel:
            self.status("Select a friend first.")
            return
        uid = sel[0]
        name = self.friends_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno(
                "Confirm", "%s %s?" % (kind.capitalize(), name)):
            return

        def work():
            try:
                if kind == "block":
                    self.api.block_user(uid, True)
                elif kind == "unblock":
                    self.api.block_user(uid, False)
                elif kind == "mute":
                    self.api.mute_user(uid, True)
                else:
                    self.api.mute_user(uid, False)
                self.after(0, lambda: self.status("%s done: %s"
                                                  % (kind, name)))
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("%sing %s..." % (kind, name))

    def _load_friends(self):
        def work():
            try:
                friends = self.api.friends_online(
                    include_offline=self.friends_offline.get())

                def fill():
                    self.friends_tree.delete(*self.friends_tree.get_children())
                    for frn in friends:
                        self.friends_tree.insert(
                            "", "end", iid=frn["id"] or frn["name"],
                            values=(frn["name"], frn["status"], frn["world"]))
                    self.status("%d friend(s) online." % len(friends))
                self.after(0, fill)
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Loading friends...")

    def _load_avatars(self):
        def work():
            try:
                avatars = self.api.my_avatars()

                def fill():
                    self._fill_avatars(avatars)
                    self.status("%d avatar(s) loaded." % len(avatars))
                self.after(0, fill)
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Loading avatars...")

    def _fill_avatars(self, avatars):
        self.avatar_tree.delete(*self.avatar_tree.get_children())
        for a in avatars:
            self.avatar_tree.insert("", "end", iid=a["id"],
                                    values=(a["name"], a["author"]))

    def _search_avatars(self):
        q = self.av_search.get().strip()
        if not q:
            self.status("Type an avatar name to search.")
            return

        def work():
            try:
                avatars = self.api.search_public_avatars(q)

                def fill():
                    self._fill_avatars(avatars)
                    self.status("Public search: %d result(s)." % len(avatars))
                self.after(0, fill)
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Searching public avatars...")

    def _equip_avatar(self):
        sel = self.avatar_tree.selection()
        if not sel:
            self.status("Select an avatar first.")
            return
        av_id = sel[0]

        def work():
            try:
                self.api.equip_avatar(av_id)
                name = self.avatar_tree.item(av_id, "values")[0]
                self.after(0, lambda: self._note_equip(av_id, name))
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Equipping...")

    # ---- Params tab (VRCOSC)

    def _tab_params(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Avatar Params  ")
        ttk.Label(f, text="Set avatar parameters by exact name (find names in "
                          "VRCX or your avatar descriptor).").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Label(f, text="Name:").grid(row=1, column=0, sticky="w")
        self.p_name = ttk.Entry(f, width=28)
        self.p_name.grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(f, text="Type:").grid(row=1, column=2, sticky="e")
        self.p_type = ttk.Combobox(f, values=["bool", "int", "float"], width=6,
                                   state="readonly")
        self.p_type.set("bool")
        self.p_type.grid(row=1, column=3, padx=6)
        ttk.Label(f, text="Value:").grid(row=2, column=0, sticky="w")
        self.p_value = ttk.Entry(f, width=28)
        self.p_value.insert(0, "True")
        self.p_value.grid(row=2, column=1, sticky="w", padx=6)
        ttk.Button(f, text="Send", command=self._send_param).grid(
            row=2, column=3, padx=6)

        g = ttk.LabelFrame(f, text="Quick gestures (standard names)", padding=6)
        g.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        for i, name in enumerate(GESTURES):
            ttk.Button(g, text=name, width=10,
                       command=lambda n=name: self._set_gesture(n)
                       ).grid(row=0, column=i, padx=3, pady=3)

        io = ttk.LabelFrame(f, text="Inputs", padding=6)
        io.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        ttk.Button(io, text="Jump", command=lambda: self.osc.input_jump()).grid(
            row=0, column=0, padx=3)
        ttk.Button(io, text="Look up",
                   command=lambda: self.osc.input_look(0, 1)).grid(
            row=0, column=1, padx=3)
        ttk.Button(io, text="Look down",
                   command=lambda: self.osc.input_look(0, -1)).grid(
            row=0, column=2, padx=3)
        ttk.Label(io, text="(fun with AFK avatars — use responsibly)").grid(
            row=0, column=3, padx=10)

    def _send_param(self):
        name = self.p_name.get().strip()
        if not name:
            self.status("Enter a parameter name.")
            return
        raw = self.p_value.get().strip()
        t = self.p_type.get()
        try:
            if t == "bool":
                val = raw.lower() in ("true", "1", "on", "yes")
            elif t == "int":
                val = int(raw)
            else:
                val = float(raw)
        except ValueError:
            self.status("Value doesn't match type %s." % t)
            return
        self.osc.avatar_param(name, val)
        self.status("Sent %s = %r" % (name, val))

    def _set_gesture(self, name):
        idx = GESTURES.index(name) if name in GESTURES else 0
        self.osc.avatar_param("GestureRight", idx)
        self.status("GestureRight → %s" % name)

    # ---- Media & Chat tab (MagicChatbox / VRCOSC)

    def _tab_media(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Media & Chat  ")

        # Media status
        med = ttk.LabelFrame(f, text="Media status (MagicChatbox/Nexus: show "
                                     "what you're doing)", padding=6)
        med.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.window_list = tk.Listbox(med, height=4)
        self.window_list.pack(side="left", fill="x", expand=True)
        side = ttk.Frame(med)
        side.pack(side="right", fill="y", padx=(8, 0))
        ttk.Button(side, text="Scan windows", command=self._scan_windows).pack(
            fill="x", pady=2)
        self.media_btn = ttk.Button(side, text="Show in chatbox",
                                    command=self._toggle_media)
        self.media_btn.pack(fill="x", pady=2)

        # Twitch
        tw = ttk.LabelFrame(f, text="Twitch chat relay (VRCOSC-style)", padding=6)
        tw.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Label(tw, text="Channel:").grid(row=0, column=0)
        self.tw_chan = ttk.Entry(tw, width=16)
        self.tw_chan.grid(row=0, column=1, padx=4)
        self.tw_btn = ttk.Button(tw, text="Connect", command=self._toggle_twitch)
        self.tw_btn.grid(row=0, column=2, padx=4)
        self.tw_relay = tk.BooleanVar(value=True)
        ttk.Checkbutton(tw, text="Relay to chatbox",
                        variable=self.tw_relay).grid(row=0, column=3)
        self.tw_log = scrolledtext.ScrolledText(tw, height=6, state="disabled",
                                                font=("Consolas", 9), wrap="word")
        self.tw_log.grid(row=1, column=0, columnspan=4, sticky="ew", pady=4)

        # HypeRate
        hr = ttk.LabelFrame(f, text="HypeRate heart rate (VRCOSC-style)",
                            padding=6)
        hr.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Label(hr, text="Join code:").grid(row=0, column=0)
        self.hr_code = ttk.Entry(hr, width=10)
        self.hr_code.grid(row=0, column=1, padx=4)
        self.hr_btn = ttk.Button(hr, text="Connect", command=self._toggle_hr)
        self.hr_btn.grid(row=0, column=2, padx=4)
        self.hr_relay = tk.BooleanVar(value=True)
        ttk.Checkbutton(hr, text="Show BPM in chatbox",
                        variable=self.hr_relay).grid(row=0, column=3)
        self.hr_label = ttk.Label(hr, text="— BPM")
        self.hr_label.grid(row=0, column=4, padx=10)
        ttk.Label(hr, text="Pulsoid token:").grid(row=1, column=0, sticky="w")
        self.pul_token = ttk.Entry(hr, width=18)
        self.pul_token.grid(row=1, column=1, columnspan=2, sticky="w", padx=4)
        self.pul_btn = ttk.Button(hr, text="Connect",
                                  command=self._toggle_pulsoid)
        self.pul_btn.grid(row=1, column=2, padx=4)
        ttk.Label(hr, text="(alternative HR source; get a token at "
                           "pulsoid.net)").grid(row=1, column=3, sticky="w")

        f.columnconfigure(0, weight=1)

    def _scan_windows(self):
        titles = get_window_titles()
        self.window_list.delete(0, "end")
        for t in titles:
            self.window_list.insert("end", t)
        self.status("Found %d window(s). Spotify track: %s"
                    % (len(titles), spotify_title(titles) or "none"))

    def _toggle_media(self):
        if self.media_running:
            self.media_running = False
            self.media_btn.config(text="Show in chatbox")
            self.status("Media display stopped.")
            return
        sel = self.window_list.curselection()
        if not sel:
            self.status("Scan and pick a window first.")
            return
        title = self.window_list.get(sel[0])

        def run():
            self.media_running = True
            self.media_btn.config(text="Stop")
            while self.media_running:
                titles = get_window_titles()
                cur = title
                track = spotify_title(titles)
                if track and "Spotify" in title:
                    cur = track
                elif title not in titles:
                    cur = track or title
                self.osc.chatbox("🎵 " + cur)
                for _ in range(150):  # re-read every 15s
                    if not self.media_running:
                        return
                    time.sleep(0.1)

        threading.Thread(target=run, daemon=True).start()
        self.status("Displaying media in chatbox (re-checks every 15s).")

    def _tw_log(self, text):
        self.tw_log.config(state="normal")
        self.tw_log.insert("end", text + "\n")
        self.tw_log.see("end")
        self.tw_log.config(state="disabled")

    def _toggle_twitch(self):
        if self.twitch and self.twitch.running:
            self.twitch.stop()
            self.twitch = None
            self.tw_btn.config(text="Connect")
            self.status("Twitch relay off.")
            return
        chan = self.tw_chan.get().strip().lstrip("#")
        if not chan:
            self.status("Enter a Twitch channel name.")
            return

        def on_msg(user, msg):
            def show():
                self._tw_log("%s: %s" % (user, msg))
                if self.tw_relay.get():
                    self.osc.chatbox("%s: %s" % (user, msg), notify=True)
            self.after(0, show)

        def on_status(s):
            self.after(0, lambda: self.status(s))

        self.twitch = TwitchIRC(on_message=on_msg, on_status=on_status)
        try:
            self.twitch.connect(chan)
            self.tw_btn.config(text="Disconnect")
        except Exception as e:
            self.twitch = None
            self.status("Twitch connect failed: %s" % e)

    def _toggle_pulsoid(self):
        if self.pul_running:
            self.pul_running = False
            if self.pul_ws:
                self.pul_ws.close()
            self.pul_btn.config(text="Connect")
            self.status("Pulsoid off.")
            return
        token = self.pul_token.get().strip()
        if not token:
            self.status("Paste a Pulsoid token first.")
            return

        def run():
            self.pul_running = True
            self.pul_btn.config(text="Disconnect")
            ws = WSClient("wss://dev.pulsoid.net/api/v1/data/real-time"
                          "?access_token=" + token)
            self.pul_ws = ws
            last_sent = 0
            try:
                ws.connect()
                while self.pul_running:
                    msg = ws.recv(timeout=20)
                    try:
                        d = json.loads(msg)
                    except (ValueError, TypeError):
                        continue
                    data = d.get("data", d)
                    bpm = data.get("heart_rate") or data.get("bpm") or d.get("bpm")
                    if not bpm:
                        continue

                    def show(b=bpm):
                        self.hr_label.config(text="%s BPM" % b)
                        if (self.hr_relay.get() and
                                time.time() - last_sent > 10):
                            self.osc.chatbox("Heart: %s BPM" % b)
                    self.after(0, show)
                    last_sent = time.time()
            except Exception as e:
                if self.pul_running:
                    self.after(0, lambda: self.status(
                        "Pulsoid error: %s" % e.__class__.__name__))
            finally:
                self.pul_running = False

        threading.Thread(target=run, daemon=True).start()
        self.status("Connecting to Pulsoid...")

    def _toggle_hr(self):
        if self.hr_running:
            self.hr_running = False
            if self.hr_ws:
                self.hr_ws.close()
            self.hr_btn.config(text="Connect")
            self.hr_label.config(text="— BPM")
            self.status("HypeRate off.")
            return
        code = self.hr_code.get().strip()
        if not code:
            self.status("Enter your HypeRate join code (from the HypeRate "
                        "app).")
            return

        def run():
            self.hr_running = True
            self.hr_btn.config(text="Disconnect")
            ws = WSClient(HYPHERATE_WS)
            self.hr_ws = ws
            try:
                ws.connect()
                ws.send(json.dumps({"type": "joinVas", "joinCode": code}))
                last_sent = 0
                while self.hr_running:
                    msg = ws.recv(timeout=15)
                    try:
                        d = json.loads(msg)
                    except ValueError:
                        continue
                    bpm = d.get("bpm") or d.get("value")
                    if not bpm:
                        continue

                    def show(b=bpm):
                        self.hr_label.config(text="%s BPM" % b)
                        if (self.hr_relay.get() and
                                time.time() - last_sent > 10):
                            self.osc.chatbox("❤ %s BPM" % b)
                    self.after(0, show)
                    last_sent = time.time()
            except Exception as e:
                if self.hr_running:
                    self.after(0, lambda: self.status(
                        "HypeRate error: %s" % e.__class__.__name__))
            finally:
                self.hr_running = False

        threading.Thread(target=run, daemon=True).start()
        self.status("Connecting to HypeRate...")

# ---- Worlds tab (VRCX world browser)

    def _tab_worlds(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Worlds  ")

        row = ttk.Frame(f)
        row.pack(fill="x", pady=(0, 6))
        self.world_search = ttk.Entry(row, font=("Segoe UI", 12))
        self.world_search.pack(side="left", fill="x", expand=True)
        self.world_search.bind("<Return>", lambda e: self._search_worlds())
        ttk.Button(row, text="Search", command=self._search_worlds).pack(
            side="left", padx=6)
        ttk.Button(row, text="Notifications",
                   command=self._load_notifications).pack(side="left", padx=6)

        panes = ttk.Frame(f)
        panes.pack(fill="both", expand=True)
        wl = ttk.LabelFrame(panes, text="Worlds", padding=4)
        wl.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.world_tree = ttk.Treeview(wl, columns=("name", "author", "occ"),
                                       show="headings", height=9)
        for c, w in zip(("name", "author", "occ"), (150, 100, 60)):
            self.world_tree.heading(c, text=c.capitalize())
            self.world_tree.column(c, width=w)
        self.world_tree.pack(fill="both", expand=True)
        self.world_tree.bind("<Double-1>", lambda e: self._load_instances())
        ttk.Button(wl, text="Show instances", command=self._load_instances).pack(
            fill="x", pady=3)

        il = ttk.LabelFrame(panes, text="Instances (double-click to join via "
                                        "browser link)", padding=4)
        il.grid(row=0, column=1, sticky="nsew")
        self.inst_tree = ttk.Treeview(il, columns=("location", "occ"),
                                      show="headings", height=9)
        for c, w in zip(("location", "occ"), (200, 60)):
            self.inst_tree.heading(c, text=c.capitalize())
            self.inst_tree.column(c, width=w)
        self.inst_tree.pack(fill="both", expand=True)
        self.inst_tree.bind("<Double-1>", lambda e: self._join_instance())
        ttk.Button(il, text="Join (open launch link)",
                   command=self._join_instance).pack(fill="x", pady=3)

        self.notif_log = scrolledtext.ScrolledText(f, height=5, state="disabled",
                                                   font=("Consolas", 9),
                                                   wrap="word")
        self.notif_log.pack(fill="x", pady=(6, 0))
        panes.columnconfigure(0, weight=1)
        panes.columnconfigure(1, weight=1)
        panes.rowconfigure(0, weight=1)
        self._current_world_id = None

    def _search_worlds(self):
        q = self.world_search.get().strip()
        if not q:
            self.status("Type a world name to search.")
            return

        def work():
            try:
                worlds = self.api.search_worlds(q)

                def fill():
                    self.world_tree.delete(*self.world_tree.get_children())
                    for w in worlds:
                        self.world_tree.insert("", "end", iid=w["id"], values=(
                            w["name"], w["author"], w["occupants"]))
                    self.status("%d world(s)." % len(worlds))
                self.after(0, fill)
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Searching worlds...")

    def _load_instances(self):
        sel = self.world_tree.selection()
        if not sel:
            self.status("Pick a world first.")
            return
        wid = sel[0]

        def work():
            try:
                name, wid2, insts = self.api.world_instances(wid)

                def fill():
                    self._current_world_id = wid2
                    self.inst_tree.delete(*self.inst_tree.get_children())
                    for i in insts:
                        self.inst_tree.insert("", "end", values=(
                            i["location"], i["occupants"]))
                    self.status("%s: %d live instance(s)." % (name,
                                                              len(insts)))
                self.after(0, fill)
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Loading instances...")

    def _join_instance(self):
        sel = self.inst_tree.selection()
        if not sel or not self._current_world_id:
            self.status("Pick an instance first.")
            return
        loc = self.inst_tree.item(sel[0], "values")[0]
        world_id, _, inst = loc.partition(":")
        url = ("https://vrchat.com/home/launch?worldId=%s&instanceId=%s"
               % (world_id, inst or loc))
        try:
            if sys.platform == "win32":
                os.startfile(url)  # noqa
            else:
                subprocess.Popen(["xdg-open", url])
            self.status("Opening launch link - approve it in the browser to "
                        "jump in.")
        except Exception as e:
            self.status("Could not open: %s" % e)

    def _load_notifications(self):
        def work():
            try:
                notifs = self.api.notifications()

                def fill():
                    self._log_to(self.notif_log, "--- notifications ---")
                    for n in notifs:
                        self._log_to(self.notif_log, "[%s] %s %s"
                                     % (n["type"], n["sender"][:8], n["title"]))
                    self.status("%d notification(s)." % len(notifs))
                self.after(0, fill)
            except Exception as e:
                self.after(0, lambda: self.status(str(e)[:80]))
        threading.Thread(target=work, daemon=True).start()
        self.status("Loading notifications...")

    # ---- Extras tab (VRCOSC/MCB extras)

    def _tab_extras(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Extras  ")

        afk = ttk.LabelFrame(f, text="AFK detection (VRCOSC-style)", padding=6)
        afk.grid(row=0, column=0, sticky="ew", pady=3)
        ttk.Label(afk, text="After idle (min):").grid(row=0, column=0)
        self.afk_mins = ttk.Spinbox(afk, from_=1, to=120, width=4, value=15)
        self.afk_mins.grid(row=0, column=1, padx=4)
        self.afk_btn = ttk.Button(afk, text="Start", command=self._toggle_afk)
        self.afk_btn.grid(row=0, column=2, padx=4)
        ttk.Label(afk, text="- shows 'AFK' in chatbox after idle, 'I'm back!' "
                            "when you act again").grid(row=0, column=3,
                                                       padx=8)

        sw = ttk.LabelFrame(f, text="Chatbox stopwatch", padding=6)
        sw.grid(row=1, column=0, sticky="ew", pady=3)
        ttk.Label(sw, text="Every (sec):").grid(row=0, column=0)
        self.watch_secs = ttk.Spinbox(sw, from_=5, to=300, width=4, value=10)
        self.watch_secs.grid(row=0, column=1, padx=4)
        self.watch_btn = ttk.Button(sw, text="Start",
                                    command=self._toggle_watch)
        self.watch_btn.grid(row=0, column=2, padx=4)
        ttk.Label(sw, text="- timer updating in chatbox").grid(
            row=0, column=3, padx=8)

        gc = ttk.LabelFrame(f, text="Random gesture cycler (VRCOSC "
                                    "'random emote')", padding=6)
        gc.grid(row=2, column=0, sticky="ew", pady=3)
        ttk.Label(gc, text="Every (sec):").grid(row=0, column=0)
        self.gc_secs = ttk.Spinbox(gc, from_=10, to=600, width=4, value=45)
        self.gc_secs.grid(row=0, column=1, padx=4)
        self.gc_btn = ttk.Button(gc, text="Start", command=self._toggle_gcycle)
        self.gc_btn.grid(row=0, column=2, padx=4)
        ttk.Label(gc, text="- fires a random gesture for 3s").grid(
            row=0, column=3, padx=8)

        ss = ttk.LabelFrame(ss_txt := f, text="System status (VRCNext-style)",
                            padding=6)
        ss.grid(row=3, column=0, sticky="ew", pady=3)
        ttk.Label(ss, text="Every (sec):").grid(row=0, column=0)
        self.ss_secs = ttk.Spinbox(ss, from_=30, to=3600, width=4, value=60)
        self.ss_secs.grid(row=0, column=1, padx=4)
        self.ss_btn = ttk.Button(ss, text="Start", command=self._toggle_sysstat)
        self.ss_btn.grid(row=0, column=2, padx=4)
        ttk.Label(ss, text="- battery + RAM in chatbox (Windows). One-shot:").grid(
            row=0, column=3, padx=8)
        ttk.Button(ss, text="Check now", command=self._sysstat_check_show).grid(
            row=0, column=4)

        ps = ttk.LabelFrame(f, text="PiShock (VRCOSC module - YOUR collar "
                                    "only)", padding=6)
        ps.grid(row=4, column=0, sticky="ew", pady=3)
        ttk.Label(ps, text="User:").grid(row=0, column=0)
        self.ps_user = ttk.Entry(ps, width=12)
        self.ps_user.grid(row=0, column=1, padx=3)
        ttk.Label(ps, text="API key:").grid(row=0, column=2)
        self.ps_key = ttk.Entry(ps, width=14, show="*")
        self.ps_key.grid(row=0, column=3, padx=3)
        ttk.Label(ps, text="Code:").grid(row=0, column=4)
        self.ps_code = ttk.Entry(ps, width=8)
        self.ps_code.grid(row=0, column=5, padx=3)
        ttk.Button(ps, text="Test vibe", command=lambda:
                   self._pishock(1, 20, 1)).grid(row=0, column=6, padx=4)
        ttk.Button(ps, text="Shock (low, 1s)", command=lambda:
                   self._pishock(0, 5, 1)).grid(row=0, column=7, padx=4)
        ttk.Label(ps, text="settings stay in this session only").grid(
            row=0, column=8, padx=6)

        self.extras_log = scrolledtext.ScrolledText(f, height=6,
                                                    state="disabled",
                                                    font=("Consolas", 9),
                                                    wrap="word")
        self.extras_log.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        f.columnconfigure(0, weight=1)

    def _pishock(self, op, intensity, duration):
        """PiShock web API. Op: 0=shock, 1=vibrate, 2=beep."""
        payload = {
            "Username": self.ps_user.get().strip(),
            "Apikey": self.ps_key.get().strip(),
            "Code": self.ps_code.get().strip(),
            "Name": "VRCHub",
            "Op": op,
            "Intensity": intensity,
            "Duration": duration,
        }
        if not all((payload["Username"], payload["Apikey"], payload["Code"])):
            self.status("Fill PiShock user/key/code first.")
            return

        def work():
            try:
                req = urllib.request.Request(
                    "https://do.pishock.com/api/apioperate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json",
                             "User-Agent": "VRCHub/" + APP_VERSION})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    body = resp.read().decode("utf-8", "replace")[:80]

                def ok():
                    self._log_to(self.extras_log, "PiShock ok: %s" % body)
                    self.status("PiShock sent.")
                self.after(0, ok)
            except Exception as e:
                msg = "PiShock failed: %s" % e.__class__.__name__

                def bad():
                    self._log_to(self.extras_log, msg)
                self.after(0, bad)
        threading.Thread(target=work, daemon=True).start()
        self.status("PiShock sending...")

    def _toggle_afk(self):
        if self.afk_running:
            self.afk_running = False
            self.afk_btn.config(text="Start")
            self.status("AFK watch off.")
            return
        try:
            mins = max(1, int(float(self.afk_mins.get())))
        except ValueError:
            mins = 15

        def run():
            self.afk_running = True
            self.afk_btn.config(text="Stop")
            while self.afk_running:
                idle = time.time() - self.last_activity
                if idle > mins * 60 and not self._afk_sent:
                    self.osc.chatbox("AFK")
                    self._afk_sent = True

                    def note():
                        self._log_to(self.extras_log, "AFK message sent")
                    self.after(0, note)
                elif idle < 10 and self._afk_sent:
                    self._afk_sent = False
                    self.osc.chatbox("I'm back!")
                time.sleep(2)

        threading.Thread(target=run, daemon=True).start()
        self.status("AFK watch on (%d min)." % mins)

    def _toggle_watch(self):
        if self.watch_running:
            self.watch_running = False
            self.watch_btn.config(text="Start")
            self.status("Stopwatch off.")
            return
        try:
            secs = max(5, int(float(self.watch_secs.get())))
        except ValueError:
            secs = 10

        def run():
            self.watch_running = True
            self.watch_btn.config(text="Stop")
            t0 = time.time()
            while self.watch_running:
                dt = int(time.time() - t0)
                self.osc.chatbox("%02d:%02d" % (dt // 60, dt % 60))
                for _ in range(secs * 10):
                    if not self.watch_running:
                        return
                    time.sleep(0.1)

        threading.Thread(target=run, daemon=True).start()
        self.status("Stopwatch on (%ds updates)." % secs)

    def _toggle_gcycle(self):
        if self.gcycle_running:
            self.gcycle_running = False
            self.gc_btn.config(text="Start")
            self.status("Gesture cycler off.")
            return
        try:
            secs = max(10, int(float(self.gc_secs.get())))
        except ValueError:
            secs = 45

        def run():
            self.gcycle_running = True
            self.gc_btn.config(text="Stop")
            while self.gcycle_running:
                g = random.choice(GESTURES)
                self.osc.avatar_param("GestureRight", GESTURES.index(g))
                time.sleep(3)
                if not self.gcycle_running:
                    return
                self.osc.avatar_param("GestureRight", 0)
                for _ in range(secs * 10):
                    if not self.gcycle_running:
                        return
                    time.sleep(0.1)

        threading.Thread(target=run, daemon=True).start()
        self.status("Gesture cycler on (%ds)." % secs)

    def _sysstat_check(self):
        batt = battery_percent()
        ram = ram_usage()
        parts = []
        if batt is not None:
            parts.append("Battery %d%%" % batt)
        if ram:
            parts.append("RAM %s/%s GB" % ram)
        return " | ".join(parts) if parts else None

    def _sysstat_check_show(self):
        msg = self._sysstat_check()
        if msg:
            self.osc.chatbox(msg)
            self.status(msg)
        else:
            self.status("System stats need Windows (or no battery/RAM data).")

    def _toggle_sysstat(self):
        if self.sysstat_running:
            self.sysstat_running = False
            self.ss_btn.config(text="Start")
            self.status("System status off.")
            return
        try:
            secs = max(30, int(float(self.ss_secs.get())))
        except ValueError:
            secs = 60

        def run():
            self.sysstat_running = True
            self.ss_btn.config(text="Stop")
            while self.sysstat_running:
                msg = self._sysstat_check()
                if msg:
                    self.osc.chatbox(msg)
                for _ in range(secs * 10):
                    if not self.sysstat_running:
                        return
                    time.sleep(0.1)

        threading.Thread(target=run, daemon=True).start()
        self.status("System status on (%ds)." % secs)

# ---- Connections tab (talk to the other apps)

    def _tab_connect(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Connections  ")

        det = ttk.LabelFrame(f, text="App detection", padding=6)
        det.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.det_label = ttk.Label(det, text="Hit Scan to see which apps are running.")
        self.det_label.pack(side="left", fill="x", expand=True)
        ttk.Button(det, text="Scan", command=self._detect_apps).pack(side="left")

        # VRCX websocket (VRCX Settings -> WebSocket Server, default port 9739)
        vx = ttk.LabelFrame(f, text="VRCX WebSocket (enable in VRCX: Settings → "
                                    "WebSocket Server)", padding=6)
        vx.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Label(vx, text="Host:").grid(row=0, column=0)
        self.vrcx_host = ttk.Entry(vx, width=14)
        self.vrcx_host.insert(0, "127.0.0.1")
        self.vrcx_host.grid(row=0, column=1, padx=4)
        ttk.Label(vx, text="Port:").grid(row=0, column=2)
        self.vrcx_port = ttk.Entry(vx, width=6)
        self.vrcx_port.insert(0, "9739")
        self.vrcx_port.grid(row=0, column=3, padx=4)
        ttk.Label(vx, text="Token:").grid(row=0, column=4)
        self.vrcx_token = ttk.Entry(vx, width=14)
        self.vrcx_token.grid(row=0, column=5, padx=4)
        self.vrcx_btn = ttk.Button(vx, text="Connect", command=self._toggle_vrcx)
        self.vrcx_btn.grid(row=0, column=6, padx=4)
        self.vrcx_relay = tk.BooleanVar(value=True)
        ttk.Checkbutton(vx, text="Announce friend joins/leaves in chatbox",
                        variable=self.vrcx_relay).grid(row=1, column=0,
                                                       columnspan=7,
                                                       sticky="w", pady=2)
        self.vrcx_log = scrolledtext.ScrolledText(vx, height=8, state="disabled",
                                                  font=("Consolas", 9),
                                                  wrap="word")
        self.vrcx_log.grid(row=2, column=0, columnspan=7, sticky="ew", pady=4)

        # OSC listener (the shared wire between all five apps)
        ol = ttk.LabelFrame(f, text="OSC listener — live traffic between VRChat "
                                     "and your apps (VRCX uses 9001)", padding=6)
        ol.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Label(ol, text="Port:").grid(row=0, column=0)
        self.osc_port = ttk.Entry(ol, width=6)
        self.osc_port.insert(0, "9001")
        self.osc_port.grid(row=0, column=1, padx=4)
        self.osc_btn = ttk.Button(ol, text="Listen", command=self._toggle_osc_listener)
        self.osc_btn.grid(row=0, column=2, padx=4)
        ttk.Label(ol, text="(chatbox/params events typed via VRCX, VRCOSC or "
                            "MagicChatbox show up here)").grid(
            row=0, column=3, sticky="w", padx=8)
        self.osc_log = scrolledtext.ScrolledText(ol, height=8, state="disabled",
                                                 font=("Consolas", 9), wrap="word")
        self.osc_log.grid(row=1, column=0, columnspan=4, sticky="ew", pady=4)
        f.columnconfigure(0, weight=1)
        vx.columnconfigure(0, weight=1)
        ol.columnconfigure(0, weight=1)

    def _detect_apps(self):
        procs = running_processes()
        ports = {"VRCX websocket (9739)": 9739}
        lines = []
        for label, exe, hints in [
                ("VRCX", "vrcx.exe", ("vrcx",)),
                ("VRCOSC", "vrcosc.exe", ("vrcosc",)),
                ("MagicChatbox", "magicchatbox.exe", ("magicchatbox",)),
                ("VRChat", "vrchat.exe", ("vrchat",))]:
            found = any(h in p for p in procs for h in hints)
            lines.append("%s: %s" % (label, "RUNNING" if found else "not running"))
        for label, port in ports.items():
            lines.append("%s: %s" % (label,
                                     "OPEN" if check_port("127.0.0.1", port)
                                     else "closed"))
        self.det_label.config(text="  |  ".join(lines))
        self.status("Scan done (%d processes)." % len(procs))

    def _log_to(self, widget, text):
        widget.config(state="normal")
        widget.insert("end", text + "\n")
        widget.see("end")
        widget.config(state="disabled")

    def _toggle_vrcx(self):
        if self.vrcx_running:
            self.vrcx_running = False
            if self.vrcx_ws:
                self.vrcx_ws.close()
            self.vrcx_btn.config(text="Connect")
            self.status("VRCX link off.")
            return
        host = self.vrcx_host.get().strip() or "127.0.0.1"
        try:
            port = int(self.vrcx_port.get())
        except ValueError:
            port = 9739
        token = self.vrcx_token.get().strip()

        def run():
            self.vrcx_running = True
            self.vrcx_btn.config(text="Disconnect")
            base = "ws://%s:%d" % (host, port)
            paths = ["/ws", "/", "/?token=%s" % token, "/ws?token=%s" % token]
            while self.vrcx_running:
                ws, last_err = None, None
                for path in paths:
                    try:
                        w = WSClient(base + path)
                        w.connect()
                        if token:
                            # best-effort auth message for token-based builds
                            w.send(json.dumps(
                                {"type": "auth", "json": {"token": token}}))
                        ws = w
                        break
                    except OSError as e:
                        last_err = e
                if not ws:
                    if self.vrcx_running:
                        self.after(0, lambda: self._log_to(
                            self.vrcx_log, "Connect failed on %s (%s) — retrying "
                            "in 5s. Is VRCX running with WebSocket Server on?"
                            % (base, last_err.__class__.__name__)))
                    time.sleep(5)
                    continue
                self.after(0, lambda: self._log_to(
                    self.vrcx_log, "Connected %s" % ws.path))
                self.vrcx_ws = ws
                try:
                    while self.vrcx_running:
                        msg = ws.recv(timeout=15)
                        if not msg:
                            continue
                        self._vrcx_event(msg)
                except Exception:
                    pass
                ws.close()
                if self.vrcx_running:
                    time.sleep(3)

        threading.Thread(target=run, daemon=True).start()
        self.status("Connecting to VRCX...")

    def _vrcx_event(self, msg):
        def show():
            try:
                d = json.loads(msg)
            except ValueError:
                self._log_to(self.vrcx_log, msg[:200])
                return
            etype = d.get("type", "")
            j = d.get("json", {})
            # VRCX pushes events; friend-join style events carry user names
            text = (j.get("user") or {}).get("displayName", "")
            line = "%s %s" % (etype, text or json.dumps(d)[:120])
            self._log_to(self.vrcx_log, line)
            if (self.vrcx_relay.get() and text and
                    any(k in etype.lower() for k in
                        ("join", "left", "notif", "location"))):
                if "left" in etype.lower():
                    self.osc.chatbox("%s left" % text, notify=True)
                else:
                    self.osc.chatbox("%s joined" % text, notify=True)
        self.after(0, show)

    def _toggle_osc_listener(self):
        if self.osc_listening:
            self.osc_listener.stop()
            self.osc_listening = False
            self.osc_btn.config(text="Listen")
            self.status("OSC listener off.")
            return
        try:
            port = int(self.osc_port.get())
        except ValueError:
            port = 9001

        def on_event(addr, args):
            def show():
                self._log_to(self.osc_log, "%s %s" % (addr, args))
            self.after(0, show)

        try:
            self.osc_listener = OSCListener("127.0.0.1", port, on_event=on_event)
            self.osc_listener.start()
            self.osc_listening = True
            self.osc_btn.config(text="Stop")
            self.status("Listening on UDP %d." % port)
        except OSError as e:
            self.status("Port %d busy: %s" % (port, e))

    # ---- Launcher tab (VRCNext)

    def _tab_tools(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Launcher  ")
        ttk.Label(f, text="Launch VRChat, VRCX, VRCOSC and MagicChatbox from "
                          "one place. Paths save to vrchub_config.json.").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.tool_paths = {}
        row = 1
        for label in DEFAULT_TOOLS:
            ttk.Label(f, text=label + ":").grid(row=row, column=0, sticky="w")
            var = tk.StringVar(value=self.cfg.get("tools", {}).get(label, ""))
            ttk.Entry(f, textvariable=var).grid(row=row, column=1,
                                                sticky="ew", padx=6)
            self.tool_paths[label] = var
            ttk.Button(f, text="Launch",
                       command=lambda v=var, l=label: self._launch(v, l)
                       ).grid(row=row, column=2)
            row += 1
        btns = ttk.Frame(f)
        btns.grid(row=row, column=0, columnspan=3, pady=(12, 0))
        ttk.Button(btns, text="Autodetect",
                   command=self._autodetect).pack(side="left", padx=3)
        ttk.Button(btns, text="Save paths",
                   command=self._save_tools).pack(side="left", padx=3)
        ttk.Button(btns, text="Launch all",
                   command=self._launch_all).pack(side="left", padx=3)
        ttk.Button(btns, text="Download missing apps",
                   command=self._open_downloads).pack(side="left", padx=3)
        f.columnconfigure(1, weight=1)

    def _launch(self, var, label):
        path = var.get().strip()
        if not path:
            self.status("No path set for %s." % label)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa
            else:
                subprocess.Popen([path])
            self.status("Launched %s." % label)
        except Exception as e:
            messagebox.showerror(APP_NAME, "Could not launch %s:\n%s" % (label, e))

    def _launch_all(self):
        for label, var in self.tool_paths.items():
            if var.get().strip():
                self._launch(var, label)

    def _autodetect(self):
        self.status("Scanning for installed tools...")
        found = autodetect(DEFAULT_TOOLS)
        for label, path in found.items():
            self.tool_paths[label].set(path)
        self.status("Autodetect found %d tool(s)." % len(found))

    def _save_tools(self):
        self.cfg["tools"] = {l: v.get() for l, v in self.tool_paths.items()}
        save_config(self.cfg)
        self.status("Paths saved.")

    def _open_downloads(self):
        urls = [
            "https://github.com/vrcx-team/VRCX/releases",
            "https://github.com/vrcx/VRCX/releases/latest",
            "https://github.com/vrcx/VRCOSC/releases/latest",
            "https://github.com/you-need-to/MagicChatbox/releases/latest",
        ]
        for url in urls:
            try:
                if sys.platform == "win32":
                    os.startfile(url)  # noqa
                else:
                    subprocess.Popen(["xdg-open", url])
            except Exception:
                pass
        self.status("Opening download pages (they're all free).")


def main():
    cfg = load_config()
    app = VRCHubApp(cfg)
    app.protocol("WM_DELETE_WINDOW",
                 lambda: (save_config(app.cfg), app.destroy()))
    app.mainloop()


if __name__ == "__main__":
    main()
