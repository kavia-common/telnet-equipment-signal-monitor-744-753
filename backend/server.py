#!/usr/bin/env python3
"""
Lightweight HTTP server to fetch rx-signal via Telnet and expose it via /api/rx-signal.

Environment variables:
- TELNET_HOST: Host/IP to telnet to (default: 202.39.123.124)
- TELNET_USERNAME: Username for telnet login (required)
- TELNET_PASSWORD: Password for telnet login (required)
- TELNET_TIMEOUT: Timeout in seconds for telnet operations (default: 10)
- SERVER_PORT: Port for the HTTP server (default: 8000)

Endpoint:
GET /api/rx-signal
Returns JSON: { "path": "1/1/3/2/1", "rx_signal": <float|null>, "timestamp": <ISO8601>, "error": <string|null> }
"""
import json
import os
import re
import sys
import time
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Tuple

try:
    import telnetlib
except Exception as e:
    print("Failed to import telnetlib:", e, file=sys.stderr)
    telnetlib = None  # Graceful handling until installed/available


DEFAULT_PATH = "1/1/3/2/1"

class TelnetClient:
    """Simple Telnet client wrapper to execute commands and parse output."""

    def __init__(self, host: str, username: str, password: str, timeout: float = 10.0):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout

    def _connect_and_login(self):
        if telnetlib is None:
            raise RuntimeError("telnetlib is unavailable in this environment.")

        tn = telnetlib.Telnet(self.host, timeout=self.timeout)

        # Attempt to handle typical login prompts
        # Prompts can vary: 'login:', 'username:', 'Password:'
        login_prompts = [b"login:", b"Login:", b"username:", b"Username:"]
        password_prompts = [b"Password:", b"password:"]

        # Wait for username prompt
        idx, _, _ = tn.expect(login_prompts, self.timeout)
        if idx == -1:
            # some devices prompt for password directly
            pass
        else:
            tn.write(self.username.encode("utf-8") + b"\n")

        # Wait for password prompt
        idx, _, _ = tn.expect(password_prompts, self.timeout)
        if idx == -1:
            # If not prompted yet, attempt to trigger
            time.sleep(0.3)
        tn.write(self.password.encode("utf-8") + b"\n")

        return tn

    def _execute_command(self, tn, command: str) -> str:
        # Send command and read until prompt returns. As we don't know the exact prompt,
        # we use a sleep + read_very_eager fallback with timeout loop for robustness.
        tn.write(command.encode("utf-8") + b"\n")
        deadline = time.time() + self.timeout
        chunks = []
        while time.time() < deadline:
            time.sleep(0.3)
            try:
                data = tn.read_very_eager()
            except EOFError:
                break
            if data:
                chunks.append(data.decode("utf-8", errors="ignore"))
                # Heuristic: command output likely complete if prompt-like symbol appears or output stops growing
                if re.search(r"[\r\n]?\S*[>#]\s*$", chunks[-1]):
                    break
        return "".join(chunks)

    def fetch_rx_signal(self, target_path: str = DEFAULT_PATH) -> Tuple[Optional[float], str]:
        """
        Connects via Telnet, executes 'show equipment ont optics', and parses rx-signal for target_path.

        Returns:
            (rx_signal_value, raw_output)
        """
        tn = None
        raw_output = ""
        try:
            tn = self._connect_and_login()
            raw_output = self._execute_command(tn, "terminal length 0")  # avoid paging if supported
            raw_output = self._execute_command(tn, "show equipment ont optics")
        finally:
            if tn is not None:
                try:
                    tn.write(b"exit\n")
                except Exception:
                    pass
                try:
                    tn.close()
                except Exception:
                    pass

        value = self._parse_rx_signal(raw_output, target_path)
        return value, raw_output

    @staticmethod
    def _parse_rx_signal(output: str, target_path: str) -> Optional[float]:
        """
        Attempt to parse the rx-signal value for the given target path from the command output.

        This uses a few patterns to be resilient to different vendor outputs.

        Example patterns it may match:
        - "1/1/3/2/1 ... rx-signal: -19.2 dBm"
        - "ONT 1/1/3/2/1   Rx optical power: -18.7 dBm"
        - "path 1/1/3/2/1 rx: -17.5 dBm"
        """
        # Restrict to the section that mentions the target path, within a reasonable neighborhood
        # to avoid matching unrelated ONTs.
        # We'll capture up to 10 lines following the match to look for rx patterns.
        lines = output.splitlines()
        indices = [i for i, line in enumerate(lines) if target_path in line]
        search_region = []
        for idx in indices:
            start = max(0, idx - 2)
            end = min(len(lines), idx + 12)
            search_region.extend(lines[start:end])

        region_text = "\n".join(search_region) if search_region else output

        # Common rx patterns
        patterns = [
            r"rx[-\s]?signal[^:]*:\s*([-+]?\d+(?:\.\d+)?)\s*dBm",
            r"rx\s*(?:optical\s*power|power)[^:]*:\s*([-+]?\d+(?:\.\d+)?)\s*dBm",
            r"\brx[:\s]\s*([-+]?\d+(?:\.\d+)?)\s*dBm",
            r"receive(?:d)?\s*power[^:]*:\s*([-+]?\d+(?:\.\d+)?)\s*dBm",
        ]

        for pat in patterns:
            m = re.search(pat, region_text, flags=re.IGNORECASE)
            if m:
                try:
                    return float(m.group(1))
                except Exception:
                    continue

        # Fallback: try to find a number near the path line
        fallback = re.search(rf"{re.escape(target_path)}.*?([-+]?\d+(?:\.\d+)?)\s*dBm", region_text, flags=re.IGNORECASE)
        if fallback:
            try:
                return float(fallback.group(1))
            except Exception:
                pass

        return None


def iso_now() -> str:
    """Return current UTC time in ISO8601 format with 'Z' suffix."""
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the API endpoints."""

    # PUBLIC_INTERFACE
    def do_GET(self):
        """
        Handle GET requests.

        Routes:
        - /api/rx-signal: Returns JSON with current rx-signal for the configured target path.
        """
        if self.path == "/health" or self.path == "/":
            self._send_json(200, {"status": "ok", "timestamp": iso_now()})
            return

        if self.path == "/api/rx-signal":
            self.handle_rx_signal()
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        # Reduce default noisy logging, but keep stderr visibility.
        sys.stderr.write("%s - - [%s] %s\n" % (self.client_address[0],
                                               self.log_date_time_string(),
                                               format % args))

    def handle_rx_signal(self):
        host = os.getenv("TELNET_HOST", "202.39.123.124")
        username = os.getenv("TELNET_USERNAME")
        password = os.getenv("TELNET_PASSWORD")
        timeout_raw = os.getenv("TELNET_TIMEOUT", "10")
        target_path = DEFAULT_PATH

        # Validate config
        errors = []
        if not username:
            errors.append("TELNET_USERNAME is not set")
        if not password:
            errors.append("TELNET_PASSWORD is not set")
        try:
            timeout = float(timeout_raw)
        except Exception:
            timeout = 10.0
            errors.append("TELNET_TIMEOUT invalid, using default 10")

        if errors:
            self._send_json(500, {
                "path": target_path,
                "rx_signal": None,
                "timestamp": iso_now(),
                "error": "; ".join(errors)
            })
            return

        try:
            client = TelnetClient(host=host, username=username, password=password, timeout=timeout)
            value, _raw = client.fetch_rx_signal(target_path)
            self._send_json(200, {
                "path": target_path,
                "rx_signal": value,
                "timestamp": iso_now(),
                "error": None if value is not None else "Unable to parse rx-signal from device output"
            })
        except Exception as e:
            self._send_json(502, {
                "path": target_path,
                "rx_signal": None,
                "timestamp": iso_now(),
                "error": f"Backend error: {e.__class__.__name__}: {e}"
            })

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Allow CORS for local React dev server
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def run_server():
    """Entrypoint to start the HTTP server."""
    port_raw = os.getenv("SERVER_PORT", "8000")
    try:
        port = int(port_raw)
    except Exception:
        port = 8000

    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Telnet rx-signal server listening on http://0.0.0.0:{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            httpd.server_close()
        except Exception:
            pass


if __name__ == "__main__":
    run_server()
