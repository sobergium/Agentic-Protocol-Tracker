# Agentic Protocol Tracker

A working technical portfolio for AI-native financial infrastructure.

- **Protocol Explorer v0.2** — corrected, source-linked protocol corpus.
- **x402 Paid-API Sandbox v0.1** — runnable standard-library Python sandbox for authorization-first, upfront, and escrow flows.
- Explicit transaction state machines and append-only JSONL evidence logs.
- Automated failure tests for replay, service-success/settlement-failure, and delayed finality.
- A comparison of payment/service failure boundaries.

> **Boundary:** HTTP 402 negotiation and client/resource-server/facilitator roles follow current x402 concepts. Wallet signatures, token transfers, facilitator verification, chain submission, and finality are deliberately simulated—not production payment code.

## Run locally

Requires Python 3.11+; there are no third-party runtime dependencies.

```bash
cd x402-sandbox
python -m unittest discover -s tests -v
python -m x402_sandbox.demo --flow authorization
python -m x402_sandbox.demo --flow upfront
python -m x402_sandbox.demo --flow escrow
```

Run the local paid resource:

```bash
cd x402-sandbox
python -m x402_sandbox.server --port 8402
curl -i http://127.0.0.1:8402/resource
python -m x402_sandbox.client --url http://127.0.0.1:8402/resource
```

The first request returns `402 Payment Required` with `PAYMENT-REQUIRED`. The payer retries with `PAYMENT-SIGNATURE`; the server verifies, serves, settles, and returns `PAYMENT-RESPONSE`.

## Map

| Path | Purpose |
| --- | --- |
| `protocol-explorer/` | Protocol Explorer v0.2 specification review |
| `x402-sandbox/` | Sandbox, tests, audit log and flow comparison |
| `.github/workflows/test.yml` | CI test run |
| `RELEASE_NOTES.md` | Release record |

## Primary references

- [x402 documentation](https://docs.x402.org/)
- [Facilitator lifecycle](https://docs.x402.org/core-concepts/facilitator)
- [Client/server roles](https://docs.x402.org/core-concepts/client-server)
- [Coinbase x402 repository](https://github.com/coinbase/x402)
