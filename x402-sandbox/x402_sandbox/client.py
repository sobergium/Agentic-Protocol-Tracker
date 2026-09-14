from __future__ import annotations

import argparse
import base64
import json
import urllib.error
import urllib.request
from uuid import uuid4

from .engine import MockPayer


def encode(value: dict) -> str:
    return base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()


def request(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        requirements = json.loads(base64.b64decode(error.headers["PAYMENT-REQUIRED"]))
        accepted = requirements["accepts"][0]
        proof = MockPayer().authorize(
            requirements["resource"]["url"], accepted["amount"], str(uuid4())
        )
        retry = urllib.request.Request(url, headers={"PAYMENT-SIGNATURE": encode(proof)})
        try:
            with urllib.request.urlopen(retry) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as retry_error:
            return retry_error.code, json.load(retry_error)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8402/resource")
    args = parser.parse_args()
    status, body = request(args.url)
    print(status, json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
