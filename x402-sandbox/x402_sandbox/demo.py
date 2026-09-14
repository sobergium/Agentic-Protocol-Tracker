from __future__ import annotations

import argparse
import json
from uuid import uuid4

from .engine import MockPayer, Sandbox
from .model import Flow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one simulated paid-API transaction")
    parser.add_argument("--flow", choices=[item.value for item in Flow], default="authorization")
    parser.add_argument("--audit", default="audit/evidence.jsonl")
    args = parser.parse_args()

    sandbox = Sandbox(evidence_path=args.audit)
    proof = MockPayer().authorize("/resource", "1000", str(uuid4()))
    result = sandbox.process(proof, flow=Flow(args.flow))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
