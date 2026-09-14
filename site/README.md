# Portfolio Interface v0.1

Dependency-free static presentation layer for the Agentic Protocol Tracker.

## Preview locally

From the repository root:

```bash
python -m http.server 8080 --directory site
```

Open http://127.0.0.1:8080.

## Design system

The interface is derived from the Systems Over Signals identity:

- warm ivory ground;
- deep blue-green ink;
- muted teal action colour;
- editorial serif display typography;
- compact technical sans-serif and monospace evidence details;
- geometric stack/signal mark rendered as accessible SVG.

## Technical boundary

The interactive browser sandbox is a presentation model of the Python state
machine. It does not call a wallet, facilitator, chain, or the local Python
server. The runnable transaction harness remains under `x402-sandbox/`.
