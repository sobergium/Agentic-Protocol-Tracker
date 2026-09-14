from __future__ import annotations

import hashlib
import hmac
import json
import threading
from pathlib import Path
from typing import Any, Callable

from .model import Flow, State, Transaction


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class EvidenceLog:
    """Append-only JSONL audit sink; writes are flushed before execution continues."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.events: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.events.append(event)
            if self.path:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, sort_keys=True) + "\n")
                    handle.flush()


class MockPayer:
    """Deterministic HMAC proof generator. This is not a wallet signature."""

    def __init__(self, payer: str = "mock:payer", secret: bytes = b"sandbox-secret"):
        self.payer = payer
        self.secret = secret

    def authorize(self, resource: str, amount: str, nonce: str) -> dict[str, Any]:
        claim = {
            "x402Version": 2,
            "payer": self.payer,
            "resource": resource,
            "amount": amount,
            "nonce": nonce,
            "scheme": "mock-hmac",
            "network": "sandbox:local",
        }
        claim["signature"] = hmac.new(self.secret, _canonical(claim), hashlib.sha256).hexdigest()
        return claim


class MockFacilitator:
    """Simulates verify, settlement, finality, escrow lock and release."""

    def __init__(
        self,
        secret: bytes = b"sandbox-secret",
        *,
        settlement_fails: bool = False,
        release_fails: bool = False,
        finality_delay: float = 0.0,
    ):
        self.secret = secret
        self.settlement_fails = settlement_fails
        self.release_fails = release_fails
        self.finality_delay = finality_delay
        self.settled: set[str] = set()
        self.locked: set[str] = set()

    def verify(self, proof: dict[str, Any], resource: str, amount: str) -> bool:
        supplied = proof.get("signature", "")
        unsigned = {key: value for key, value in proof.items() if key != "signature"}
        expected = hmac.new(self.secret, _canonical(unsigned), hashlib.sha256).hexdigest()
        return (
            hmac.compare_digest(supplied, expected)
            and proof.get("x402Version") == 2
            and proof.get("resource") == resource
            and proof.get("amount") == amount
        )

    def settle(self, fingerprint: str, timeout: float) -> str:
        if self.finality_delay > timeout:
            return "pending"
        if self.settlement_fails:
            return "failed"
        self.settled.add(fingerprint)
        return "settled"

    def lock(self, fingerprint: str, timeout: float) -> str:
        status = self.settle(fingerprint, timeout)
        if status == "settled":
            self.settled.discard(fingerprint)
            self.locked.add(fingerprint)
            return "locked"
        return status

    def release(self, fingerprint: str) -> str:
        if self.release_fails:
            return "failed"
        self.locked.discard(fingerprint)
        self.settled.add(fingerprint)
        return "released"


class Sandbox:
    def __init__(
        self,
        facilitator: MockFacilitator | None = None,
        *,
        evidence_path: str | Path | None = "audit/evidence.jsonl",
        resource: str = "/resource",
        amount: str = "1000",
        service_timeout: float = 1.0,
    ):
        self.facilitator = facilitator or MockFacilitator()
        self.evidence = EvidenceLog(evidence_path)
        self.resource = resource
        self.amount = amount
        self.service_timeout = service_timeout
        self._reserved: set[str] = set()
        self._lock = threading.Lock()

    def requirements(self) -> dict[str, Any]:
        return {
            "x402Version": 2,
            "resource": {"url": self.resource, "description": "Sandbox paid resource"},
            "accepts": [{
                "scheme": "mock-hmac",
                "network": "sandbox:local",
                "amount": self.amount,
                "asset": "SIMULATED",
                "payTo": "mock:resource-server",
                "maxTimeoutSeconds": self.service_timeout,
            }],
            "simulation": True,
        }

    def _move(self, tx: Transaction, state: State, **data: Any) -> None:
        self.evidence.append(tx.transition(state, **data))

    @staticmethod
    def fingerprint(proof: dict[str, Any]) -> str:
        return hashlib.sha256(_canonical(proof)).hexdigest()

    def process(
        self,
        proof: dict[str, Any],
        *,
        flow: Flow = Flow.AUTHORIZATION,
        service: Callable[[], Any] = lambda: {"value": "paid resource"},
    ) -> dict[str, Any]:
        tx = Transaction(flow)
        self._move(tx, State.PAYMENT_REQUIRED, requirements=self.requirements())
        fingerprint = self.fingerprint(proof)

        # Reserve before service starts. This makes duplicate execution a local,
        # auditable invariant even when requests race.
        with self._lock:
            if fingerprint in self._reserved:
                self._move(tx, State.REPLAY_REJECTED, fingerprint=fingerprint)
                return self._result(tx, None, "duplicate_payment")
            if not self.facilitator.verify(proof, self.resource, self.amount):
                self._move(tx, State.SETTLEMENT_FAILED, reason="invalid_authorization")
                return self._result(tx, None, "invalid_authorization")
            self._reserved.add(fingerprint)

        self._move(tx, State.AUTHORIZED, fingerprint=fingerprint)

        if flow is Flow.UPFRONT:
            status = self.facilitator.settle(fingerprint, self.service_timeout)
            if status != "settled":
                target = State.SETTLEMENT_PENDING if status == "pending" else State.SETTLEMENT_FAILED
                self._move(tx, target, phase="before_service")
                return self._result(tx, None, status)
            self._move(tx, State.SETTLED, phase="before_service")

        if flow is Flow.ESCROW:
            status = self.facilitator.lock(fingerprint, self.service_timeout)
            if status != "locked":
                target = State.SETTLEMENT_PENDING if status == "pending" else State.SETTLEMENT_FAILED
                self._move(tx, target, phase="escrow_lock")
                return self._result(tx, None, status)
            self._move(tx, State.FUNDS_LOCKED)

        self._move(tx, State.SERVICE_STARTED)
        try:
            payload = service()
        except Exception as exc:
            self._move(tx, State.SERVICE_FAILED, error=type(exc).__name__)
            if flow is Flow.ESCROW:
                self.facilitator.locked.discard(fingerprint)
                self._move(tx, State.REFUNDED)
            return self._result(tx, None, "service_failed")
        self._move(tx, State.SERVICE_SUCCEEDED)

        if flow is Flow.AUTHORIZATION:
            status = self.facilitator.settle(fingerprint, self.service_timeout)
            if status != "settled":
                target = State.SETTLEMENT_PENDING if status == "pending" else State.SETTLEMENT_FAILED
                self._move(tx, target, phase="after_service")
                return self._result(tx, payload, status)
            self._move(tx, State.SETTLED, phase="after_service")

        if flow is Flow.ESCROW:
            status = self.facilitator.release(fingerprint)
            if status != "released":
                self._move(tx, State.SETTLEMENT_FAILED, phase="escrow_release", funds="locked")
                return self._result(tx, payload, "release_failed")
            self._move(tx, State.RELEASED)

        self._move(tx, State.COMPLETE)
        return self._result(tx, payload, "ok")

    @staticmethod
    def _result(tx: Transaction, payload: Any, outcome: str) -> dict[str, Any]:
        return {
            "transactionId": tx.id,
            "flow": tx.flow.value,
            "state": tx.state.value,
            "outcome": outcome,
            "serviceResult": payload,
            "history": tx.history,
        }
