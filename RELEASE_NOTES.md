# Release notes

## x402 Paid-API Sandbox v0.1.0

This release builds on Protocol Explorer v0.2 and includes:

- authorization-first, upfront and escrow execution models;
- mock payer, protected resource server and facilitator;
- explicit transaction states;
- durable JSONL evidence records;
- replay protection before service execution;
- modeled settlement failure and indeterminate finality;
- standard-library HTTP demo and client;
- automated unit and HTTP tests;
- a failure-boundary and atomicity comparison.

### Simulation disclosure

No blockchain RPC, wallet, token contract, real facilitator, cryptographic wallet
signature or production x402 SDK is used. HMAC is only a deterministic mock
authorization mechanism. The HTTP header names and high-level lifecycle follow
current x402 documentation; alternative flow models are analytical extensions.

### Reproducibility

```bash
cd x402-sandbox
python -m unittest discover -s tests -v
```
