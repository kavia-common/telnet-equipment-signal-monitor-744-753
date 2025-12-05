#!/usr/bin/env python3
"""
CLI utility to fetch rx-signal via Telnet once and print JSON to stdout.

Usage:
  python cli_fetch.py

Environment variables (same as server.py):
- TELNET_HOST (default 202.39.123.124)
- TELNET_USERNAME (required)
- TELNET_PASSWORD (required)
- TELNET_TIMEOUT (default 10)
"""
import json
import os
import sys
from server import TelnetClient, DEFAULT_PATH, iso_now

def main():
    host = os.getenv("TELNET_HOST", "202.39.123.124")
    username = os.getenv("TELNET_USERNAME")
    password = os.getenv("TELNET_PASSWORD")
    timeout_raw = os.getenv("TELNET_TIMEOUT", "10")
    try:
        timeout = float(timeout_raw)
    except Exception:
        timeout = 10.0

    if not username or not password:
        print(json.dumps({
            "path": DEFAULT_PATH,
            "rx_signal": None,
            "timestamp": iso_now(),
            "error": "TELNET_USERNAME and TELNET_PASSWORD must be set"
        }))
        sys.exit(2)

    try:
        client = TelnetClient(host=host, username=username, password=password, timeout=timeout)
        value, _ = client.fetch_rx_signal(DEFAULT_PATH)
        print(json.dumps({
            "path": DEFAULT_PATH,
            "rx_signal": value,
            "timestamp": iso_now(),
            "error": None if value is not None else "Unable to parse rx-signal from device output"
        }))
        sys.exit(0 if value is not None else 1)
    except Exception as e:
        print(json.dumps({
            "path": DEFAULT_PATH,
            "rx_signal": None,
            "timestamp": iso_now(),
            "error": f"{e.__class__.__name__}: {e}"
        }))
        sys.exit(3)

if __name__ == "__main__":
    main()
