# Backend - Telnet rx-signal Server

A minimal Python HTTP server that logs in via Telnet to the device, runs `show equipment ont optics`, parses the rx-signal for `1/1/3/2/1`, and exposes it via an HTTP endpoint.

## Requirements

- Python 3.8+
- Network connectivity to the device
- Valid credentials

## Environment Variables

- TELNET_HOST (default: 202.39.123.124)
- TELNET_USERNAME (required)
- TELNET_PASSWORD (required)
- TELNET_TIMEOUT (default: 10)
- SERVER_PORT (default: 8000)

See `../.env.example` for an example configuration.

## Install

No external packages required (uses Python stdlib: telnetlib, http.server).
Create and export environment variables or use a `.env` loader (optional if you have one in your environment).

## Run

```bash
# From repository root
cd telnet-equipment-signal-monitor-744-753/backend
export TELNET_USERNAME=youruser
export TELNET_PASSWORD=yourpass
python server.py
```

Server will listen on `http://0.0.0.0:8000`.

## API

- GET `/health` -> `{ "status": "ok", "timestamp": "..." }`
- GET `/api/rx-signal` -> 
  ```json
  {
    "path": "1/1/3/2/1",
    "rx_signal": -19.2,
    "timestamp": "2025-01-01T00:00:00Z",
    "error": null
  }
  ```

On errors, `rx_signal` will be `null` and `error` will contain a message.

## CLI Helper

You can also fetch once via CLI:

```bash
python cli_fetch.py
```

Prints a single JSON payload to stdout.
