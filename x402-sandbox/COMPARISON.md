# Flow comparison

None of the three models provides true distributed atomicity between arbitrary
service work and an external payment ledger. They move or narrow the failure
boundary.

| Model | Payment point | Service point | Dominant failure boundary | Atomicity consequence |
| --- | --- | --- | --- | --- |
| Authorization-first | Verify → serve → settle | Before final settlement | Service may succeed while settlement fails or stays pending | Favors user experience; merchant bears collection risk |
| Upfront | Verify → settle → serve | After confirmed settlement | Payment may complete while service subsequently fails | Favors collection certainty; payer needs refund/remedy |
| Escrow | Verify → lock → serve → release | Between lock and release | Release can fail after service while funds remain locked | Narrows exposure but adds locked-funds and dispute states |

## Required compensating controls

- **Authorization-first:** idempotent service execution, durable proof reservation,
reconciliation and a collection/retry policy.
- **Upfront:** durable fulfillment queue, refund policy and payment-to-job
correlation.
- **Escrow:** explicit release authority, expiry/refund rules, dispute evidence
and reconciliation.

A timeout after broadcast is modeled as `settlement_pending`, not a definitive
failure. Retrying service on that signal would risk duplicate fulfillment.
