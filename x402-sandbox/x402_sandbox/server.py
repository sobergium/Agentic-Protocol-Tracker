from __future__ import annotations

import argparse
import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import Sandbox
from .model import Flow


def encode_header(value: dict) -> str:
    return base64.b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()


def decode_header(value: str) -> dict:
    return json.loads(base64.b64decode(value, validate=True))


class PaidHandler(BaseHTTPRequestHandler):
    sandbox = Sandbox()

    def do_GET(self) -> None:
        if self.path != "/resource":
            self.send_error(404)
            return
        signature = self.headers.get("PAYMENT-SIGNATURE")
        if not signature:
            self._json(402, {"error": "payment_required"},
                       {"PAYMENT-REQUIRED": encode_header(self.sandbox.requirements())})
            return
        try:
            proof = decode_header(signature)
        except Exception:
            self._json(400, {"error": "malformed_payment_signature"})
            return
        result = self.sandbox.process(proof, flow=Flow.AUTHORIZATION)
        status = 200 if result["outcome"] == "ok" else 402
        self._json(status, result, {"PAYMENT-RESPONSE": encode_header({
            "transactionId": result["transactionId"],
            "outcome": result["outcome"],
            "simulation": True,
        })})

    def _json(self, status: int, body: dict, headers: dict[str, str] | None = None) -> None:
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8402)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PaidHandler)
    print(f"listening on http://127.0.0.1:{args.port}/resource")
    server.serve_forever()


if __name__ == "__main__":
    main()
