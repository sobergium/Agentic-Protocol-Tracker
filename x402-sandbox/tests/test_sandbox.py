from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from x402_sandbox.engine import MockFacilitator, MockPayer, Sandbox
from x402_sandbox.model import Flow


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.payer = MockPayer()
        self.proof = self.payer.authorize("/resource", "1000", "nonce-1")

    def test_requirements_are_v2_and_simulated(self):
        req = Sandbox(evidence_path=None).requirements()
        self.assertEqual(req["x402Version"], 2)
        self.assertTrue(req["simulation"])

    def test_valid_authorization_flow_completes(self):
        result = Sandbox(evidence_path=None).process(self.proof)
        self.assertEqual(result["state"], "complete")
        self.assertEqual(result["outcome"], "ok")

    def test_replay_is_rejected_before_duplicate_service(self):
        calls = []
        box = Sandbox(evidence_path=None)
        box.process(self.proof, service=lambda: calls.append("called") or {"ok": True})
        duplicate = box.process(self.proof, service=lambda: calls.append("called") or {"ok": True})
        self.assertEqual(calls, ["called"])
        self.assertEqual(duplicate["state"], "replay_rejected")
        self.assertEqual(duplicate["outcome"], "duplicate_payment")

    def test_service_success_settlement_failure_is_explicit(self):
        box = Sandbox(MockFacilitator(settlement_fails=True), evidence_path=None)
        result = box.process(self.proof)
        self.assertEqual(result["state"], "settlement_failed")
        self.assertIsNotNone(result["serviceResult"])
        states = [event["to"] for event in result["history"]]
        self.assertLess(states.index("service_succeeded"), states.index("settlement_failed"))

    def test_finality_beyond_timeout_is_pending_after_service(self):
        box = Sandbox(MockFacilitator(finality_delay=2), evidence_path=None, service_timeout=1)
        result = box.process(self.proof)
        self.assertEqual(result["state"], "settlement_pending")
        self.assertEqual(result["outcome"], "pending")
        self.assertIsNotNone(result["serviceResult"])

    def test_invalid_signature_does_not_run_service(self):
        proof = dict(self.proof)
        proof["signature"] = "bad"
        calls = []
        result = Sandbox(evidence_path=None).process(
            proof, service=lambda: calls.append("called")
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["outcome"], "invalid_authorization")

    def test_upfront_settles_before_service(self):
        result = Sandbox(evidence_path=None).process(self.proof, flow=Flow.UPFRONT)
        states = [event["to"] for event in result["history"]]
        self.assertLess(states.index("settled"), states.index("service_started"))

    def test_upfront_failure_prevents_service(self):
        calls = []
        box = Sandbox(MockFacilitator(settlement_fails=True), evidence_path=None)
        result = box.process(
            self.proof, flow=Flow.UPFRONT,
            service=lambda: calls.append("called")
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["state"], "settlement_failed")

    def test_upfront_finality_timeout_prevents_service(self):
        calls = []
        box = Sandbox(MockFacilitator(finality_delay=2), evidence_path=None, service_timeout=1)
        result = box.process(
            self.proof, flow=Flow.UPFRONT,
            service=lambda: calls.append("called")
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["state"], "settlement_pending")

    def test_escrow_locks_then_releases(self):
        result = Sandbox(evidence_path=None).process(self.proof, flow=Flow.ESCROW)
        states = [event["to"] for event in result["history"]]
        self.assertLess(states.index("funds_locked"), states.index("service_started"))
        self.assertLess(states.index("service_succeeded"), states.index("released"))
        self.assertEqual(result["state"], "complete")

    def test_escrow_release_failure_leaves_explicit_failure(self):
        box = Sandbox(MockFacilitator(release_fails=True), evidence_path=None)
        result = box.process(self.proof, flow=Flow.ESCROW)
        self.assertEqual(result["outcome"], "release_failed")
        self.assertEqual(result["state"], "settlement_failed")
        self.assertIsNotNone(result["serviceResult"])

    def test_escrow_service_failure_refunds(self):
        def fail():
            raise RuntimeError("boom")
        result = Sandbox(evidence_path=None).process(
            self.proof, flow=Flow.ESCROW, service=fail
        )
        self.assertEqual(result["state"], "refunded")
        self.assertEqual(result["outcome"], "service_failed")

    def test_evidence_persists_as_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            box = Sandbox(evidence_path=path)
            result = box.process(self.proof)
            events = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(events), len(result["history"]))
            self.assertEqual(events[-1]["to"], "complete")

    def test_wrong_amount_is_rejected(self):
        proof = self.payer.authorize("/resource", "999", "nonce-2")
        result = Sandbox(evidence_path=None).process(proof)
        self.assertEqual(result["outcome"], "invalid_authorization")

    def test_transaction_history_is_sequenced(self):
        result = Sandbox(evidence_path=None).process(self.proof)
        self.assertEqual(
            [event["sequence"] for event in result["history"]],
            list(range(1, len(result["history"]) + 1)),
        )


if __name__ == "__main__":
    unittest.main()
