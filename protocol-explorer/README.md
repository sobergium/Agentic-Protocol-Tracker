# Protocol Explorer v0.2

A compact primary-source corpus used by the transaction harness.

## Corrections applied

1. **HTTP negotiation:** current x402 documentation uses a `402 Payment Required`
response with Base64-encoded `PAYMENT-REQUIRED`, followed by a retry carrying
Base64-encoded `PAYMENT-SIGNATURE`.
2. **Roles:** the client constructs a payment payload; the resource server
enforces requirements; a facilitator can verify and settle.
3. **Execution order:** current facilitator documentation describes verification,
service fulfillment, and settlement, with `PAYMENT-RESPONSE` returned to the
client. Therefore service success and settlement success are separate facts.
4. **Finality:** a broadcast transaction whose confirmation cannot be established
may be non-terminal (`settlement_pending`), so timeout is not equivalent to
payment failure.
5. **Replay:** a signed payload can be submitted more than once. The sandbox
reserves a proof fingerprint before service execution; this is a local control,
not a claim that every scheme has identical replay semantics.
6. **Versioning:** this project models the v2 header vocabulary and includes
`x402Version: 2`; it does not assert wire compatibility with every scheme.

## Primary sources (checked 2026-09-14)

- https://docs.x402.org/core-concepts/http-402
- https://docs.x402.org/core-concepts/client-server
- https://docs.x402.org/core-concepts/facilitator
- https://docs.x402.org/getting-started/quickstart-for-sellers
- https://github.com/coinbase/x402

## Scope labels

| Element | Status |
| --- | --- |
| HTTP 402 challenge/retry shape | Protocol-informed |
| Header names and Base64 JSON envelope | Protocol-informed |
| Mock HMAC payer proof | Simulated |
| Facilitator verification/settlement | Simulated |
| Chain finality and transaction hash | Simulated |
| Upfront and escrow variants | Analytical extensions |
| JSONL governance evidence | Project-specific control |
