# x402 Paid-API Sandbox v0.1

A local, zero-runtime-dependency transaction harness for examining how payment
and service execution separate under failure.

## Components

- `MockPayer`: creates a deterministic mock authorization proof.
- `PaidHandler`: HTTP protected resource using x402-style headers.
- `MockFacilitator`: simulates verification, settlement, finality and escrow.
- `Sandbox`: executes explicit state transitions and reserves proofs.
- `EvidenceLog`: flushes append-only JSONL state evidence.

## Setup

```bash
python --version  # 3.11+
python -m unittest discover -s tests -v
```

No install is required when commands are run from this directory. Optional:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Run

```bash
python -m x402_sandbox.demo --flow authorization
python -m x402_sandbox.demo --flow upfront
python -m x402_sandbox.demo --flow escrow
python -m x402_sandbox.server
```

In another terminal:

```bash
python -m x402_sandbox.client
```

Evidence is written to `audit/evidence.jsonl`.

## Genuine vs simulated

| Component | Classification |
| --- | --- |
| HTTP 402 challenge and retry pattern | Protocol-informed implementation |
| `PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE`, `PAYMENT-RESPONSE` | Protocol-informed vocabulary |
| Base64 JSON envelope | Protocol-informed |
| HMAC “signature” | Simulation |
| Network, asset, address and ledger | Simulation |
| Facilitator verification and settlement | Simulation |
| Upfront/escrow orchestration | Analytical extension |
| Evidence JSONL | Project governance control |

Do not use this project to custody funds or authorize real transfers.
