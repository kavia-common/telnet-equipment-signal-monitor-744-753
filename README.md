# telnet-equipment-signal-monitor-744-753

This repository includes:
- A lightweight Python backend (`backend/`) exposing `/api/rx-signal` which telnet-logins to the device, runs `show equipment ont optics`, parses `rx-signal` for path `1/1/3/2/1`, and returns JSON.
- A minimal React frontend (`react_frontend/`) that displays the rx-signal and lets you refresh.

Quick start:

1) Configure environment variables (see `.env.example`)
2) Start backend:
```bash
cd telnet-equipment-signal-monitor-744-753/backend
export TELNET_USERNAME=youruser
export TELNET_PASSWORD=yourpass
python server.py
```

3) Start frontend:
```bash
cd telnet-equipment-signal-monitor-744-753/react_frontend
REACT_APP_API_BASE=http://localhost:8000 npm start
```

Then open http://localhost:3000 and press Refresh to fetch latest rx value.