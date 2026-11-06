import os
import sys
import socket
import ssl
import importlib.util

# ---------------------------------------------------------------------------
# Clarity Makcu V2.9 - cracked launcher
#
# v2.9 dropped the full-URL transport. It resolves "keyauth.win" itself, runs
# it through a Cloudflare-only IP filter (_cf_ipv4) that drops loopback/
# private/reserved/link-local addresses, then connects to the picked IP over
# TLS and POSTs /api/1.3/. A plain 127.0.0.1 redirect gets filtered out, so we:
#   1. resolve the auth hosts to a fake Cloudflare IP the filter keeps,
#   2. translate that IP back to 127.0.0.1 (and 443 -> 8443) at connect time,
#   3. strip TLS so the plain-HTTP local mock answers directly.
# No pyd bytes are touched.
# ---------------------------------------------------------------------------

_REDIRECT_HOSTS = {"keyauth.win", "api.platoboost.com", "api.platoboost.net"}
_FAKE_CF = "104.16.0.1"   # inside _OK_NETS (104.16.0.0/13), not loopback/private
_MOCK_HOST = "127.0.0.1"
_REAL_PORT = 443
_MOCK_PORT = 8443


# 1) auth hosts -> fake Cloudflare IP
_orig_getaddrinfo = socket.getaddrinfo


def _crack_getaddrinfo(host, port, *a, **k):
    if host in _REDIRECT_HOSTS:
        host = _FAKE_CF
    return _orig_getaddrinfo(host, port, *a, **k)


socket.getaddrinfo = _crack_getaddrinfo


# 2) fake CF IP -> localhost, 443 -> 8443
_orig_create_connection = socket.create_connection


def _crack_create_connection(addr, *a, **k):
    if isinstance(addr, tuple) and len(addr) >= 2:
        host, port = addr[0], addr[1]
        if host == _FAKE_CF:
            host = _MOCK_HOST
        if port == _REAL_PORT:
            port = _MOCK_PORT
        if (host, port) != (addr[0], addr[1]):
            addr = (host, port) + tuple(addr[2:])
    return _orig_create_connection(addr, *a, **k)


socket.create_connection = _crack_create_connection

try:
    import http.client as _hc

    _hc.HTTPConnection._create_connection = _crack_create_connection
except Exception:
    pass


# 3) strip TLS
_orig_wrap_socket = ssl.SSLContext.wrap_socket


def _crack_wrap_socket(self, sock, *a, **k):
    return sock


ssl.SSLContext.wrap_socket = _crack_wrap_socket


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------
_extra = os.path.dirname(os.path.abspath(sys.argv[0]))
_root = os.path.dirname(_extra)
sys.path.append(_extra)
os.chdir(_root)

_stale = os.path.join(_extra, "main.py")
if os.path.exists(_stale):
    os.remove(_stale)

_pyd = os.path.join(_extra, "main.cp310-win_amd64.pyd")
_spec = importlib.util.spec_from_file_location("main", _pyd)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["main"] = _mod
_spec.loader.exec_module(_mod)
