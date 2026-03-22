from __future__ import annotations

import argparse
import json
import socketserver
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from .scheduler import AdmissionConfig, AdaptiveAdmissionController


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def make_handler(controller: AdaptiveAdmissionController, backend_base_url: str):
    class AdaptiveProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args) -> None:
            return

        def _send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._send_json({"ok": True, "service": "vllm_adaptive_proxy"})
                return
            if self.path == "/scheduler_stats":
                self._send_json(controller.snapshot())
                return
            self._proxy_request(body=None)

        def do_POST(self) -> None:
            body_len = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(body_len) if body_len > 0 else b""
            self._proxy_request(body=body)

        def _proxy_request(self, body: bytes | None) -> None:
            if self.command == "POST" and self.path.startswith("/v1/completions"):
                self._proxy_completion(body or b"")
                return

            target_url = f"{backend_base_url}{self.path}"
            request = urllib.request.Request(target_url, data=body, method=self.command)
            for key, value in self.headers.items():
                if key.lower() == "host":
                    continue
                request.add_header(key, value)
            try:
                with urllib.request.urlopen(request, timeout=300) as resp:
                    payload = resp.read()
                    self.send_response(resp.status)
                    for key, value in resp.headers.items():
                        if key.lower() in {"connection", "transfer-encoding", "content-length"}:
                            continue
                        self.send_header(key, value)
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                self.send_response(exc.code)
                for key, value in exc.headers.items():
                    if key.lower() in {"connection", "transfer-encoding", "content-length"}:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=502)

        def _proxy_completion(self, body: bytes) -> None:
            stream = False
            try:
                payload = json.loads(body.decode("utf-8"))
                stream = bool(payload.get("stream", False))
            except Exception:
                payload = None

            acquired = False
            try:
                ticket = controller.acquire()
                acquired = True
                target_url = f"{backend_base_url}{self.path}"
                request = urllib.request.Request(target_url, data=body, method="POST")
                for key, value in self.headers.items():
                    if key.lower() == "host":
                        continue
                    request.add_header(key, value)

                with urllib.request.urlopen(request, timeout=3600) as resp:
                    self.send_response(resp.status)
                    for key, value in resp.headers.items():
                        if key.lower() in {"connection", "transfer-encoding", "content-length"}:
                            continue
                        self.send_header(key, value)
                    self.send_header("X-Adaptive-Gate-Wait-MS", str(ticket["gate_wait_ms"]))

                    if stream:
                        self.end_headers()
                        for chunk in resp:
                            if not chunk:
                                continue
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    else:
                        payload_bytes = resp.read()
                        self.send_header("Content-Length", str(len(payload_bytes)))
                        self.end_headers()
                        if payload_bytes:
                            self.wfile.write(payload_bytes)
                            self.wfile.flush()
            except urllib.error.HTTPError as exc:
                payload_bytes = exc.read()
                self.send_response(exc.code)
                for key, value in exc.headers.items():
                    if key.lower() in {"connection", "transfer-encoding", "content-length"}:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                if payload_bytes:
                    self.wfile.write(payload_bytes)
            except TimeoutError as exc:
                self._send_json({"error": str(exc), "scheduler": controller.snapshot()}, status=429)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=502)
            finally:
                if acquired:
                    controller.release()

    return AdaptiveProxyHandler


def parse_args():
    parser = argparse.ArgumentParser(description="Adaptive admission-control proxy for vLLM serve")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--backend_base_url", type=str, required=True)
    parser.add_argument("--kv_cache_high_watermark", type=float, default=0.85)
    parser.add_argument("--waiting_high_watermark", type=int, default=128)
    parser.add_argument("--running_high_watermark", type=int, default=128)
    parser.add_argument("--max_proxy_inflight", type=int, default=128)
    parser.add_argument("--poll_interval_sec", type=float, default=0.05)
    parser.add_argument("--max_gate_wait_sec", type=float, default=300.0)
    return parser.parse_args()


def main():
    args = parse_args()
    controller = AdaptiveAdmissionController(
        AdmissionConfig(
            backend_base_url=args.backend_base_url,
            kv_cache_high_watermark=args.kv_cache_high_watermark,
            waiting_high_watermark=args.waiting_high_watermark,
            running_high_watermark=args.running_high_watermark,
            max_proxy_inflight=args.max_proxy_inflight,
            poll_interval_sec=args.poll_interval_sec,
            max_gate_wait_sec=args.max_gate_wait_sec,
        )
    )
    handler = make_handler(controller, args.backend_base_url)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"[INFO] Adaptive proxy listening on http://{args.host}:{args.port}")
    print(f"[INFO] backend_base_url={args.backend_base_url}")
    print(f"[INFO] kv_cache_high_watermark={args.kv_cache_high_watermark}")
    print(f"[INFO] waiting_high_watermark={args.waiting_high_watermark}")
    print(f"[INFO] running_high_watermark={args.running_high_watermark}")
    print(f"[INFO] max_proxy_inflight={args.max_proxy_inflight}")
    server.serve_forever()


if __name__ == "__main__":
    main()
