from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from typing import Any
from uuid import uuid4


class Flow(StrEnum):
    AUTHORIZATION = "authorization"
    UPFRONT = "upfront"
    ESCROW = "escrow"


class State(StrEnum):
    CREATED = "created"
    PAYMENT_REQUIRED = "payment_required"
    AUTHORIZED = "authorized"
    FUNDS_LOCKED = "funds_locked"
    SERVICE_STARTED = "service_started"
    SERVICE_SUCCEEDED = "service_succeeded"
    SERVICE_FAILED = "service_failed"
    SETTLEMENT_PENDING = "settlement_pending"
    SETTLED = "settled"
    SETTLEMENT_FAILED = "settlement_failed"
    RELEASED = "released"
    REFUNDED = "refunded"
    REPLAY_REJECTED = "replay_rejected"
    COMPLETE = "complete"


@dataclass
class Transaction:
    flow: Flow
    id: str = field(default_factory=lambda: str(uuid4()))
    state: State = State.CREATED
    history: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, state: State, **evidence: Any) -> dict[str, Any]:
        event = {
            "sequence": len(self.history) + 1,
            "timestamp": time(),
            "transactionId": self.id,
            "flow": self.flow.value,
            "from": self.state.value,
            "to": state.value,
            "evidence": evidence,
        }
        self.state = state
        self.history.append(event)
        return event
