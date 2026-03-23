from __future__ import annotations

import argparse
import json
import socketserver
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from .scheduler import LengthAwareScheduler, SchedulerConfig


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 512


def make_handler(scheduler: LengthAwareScheduler, backend_base_url: str):
    class LengthAwareProxyHandler(BaseHTTPRequestHandler):
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
                self._send_json({"ok": True, "service": "vllm_length_aware_proxy_v5"})
                return
            if self.path == "/scheduler_stats":
                self._send_json(scheduler.snapshot())
                return
            self._proxy_passthrough(body=None)

        def do_POST(self) -> None:
            body_len = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(body_len) if body_len > 0 else b""
            if self.path.startswith("/v1/completions"):
                self._proxy_completion(body)
                return
            self._proxy_passthrough(body=body)

        def _proxy_passthrough(self, body: bytes | None) -> None:
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
            payload = None
            stream = False
            request_start = time.perf_counter()
            first_chunk_time = None
            latency_ms = None
            ttft_ms = None
            try:
                payload = json.loads(body.decode("utf-8"))
                stream = bool(payload.get("stream", False))
            except Exception:
                pass

            acquired = False
            try:
                ticket = scheduler.acquire(payload.get("prompt") if isinstance(payload, dict) else None)
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
                    self.send_header("X-Length-Aware-Bucket", ticket["bucket"])
                    self.send_header("X-Length-Aware-Prompt-Chars", str(ticket["prompt_chars"]))
                    self.send_header("X-Length-Aware-Gate-Wait-MS", str(ticket["gate_wait_ms"]))

                    if stream:
                        self.end_headers()
                        for chunk in resp:
                            if not chunk:
                                continue
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter()
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    else:
                        payload_bytes = resp.read()
                        self.send_header("Content-Length", str(len(payload_bytes)))
                        self.end_headers()
                        if payload_bytes:
                            first_chunk_time = time.perf_counter()
                            self.wfile.write(payload_bytes)
                            self.wfile.flush()
                    end_time = time.perf_counter()
                    if first_chunk_time is None:
                        first_chunk_time = end_time
                    ttft_ms = round((first_chunk_time - request_start) * 1000, 2)
                    latency_ms = round((end_time - request_start) * 1000, 2)
            except urllib.error.HTTPError as exc:
                payload_bytes = exc.read()
                self.send_response(exc.code)
                for key, value in exc.headers.items():
                    if key.lower() in {"connection", "transfer-encoding", "content-length"}:
                        continue
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload_bytes)))
                self.end_headers()
                if payload_bytes:
                    self.wfile.write(payload_bytes)
            except TimeoutError as exc:
                self._send_json({"error": str(exc), "scheduler": scheduler.snapshot()}, status=429)
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=502)
            finally:
                if acquired:
                    scheduler.release(ticket=ticket, ttft_ms=ttft_ms, latency_ms=latency_ms)

    return LengthAwareProxyHandler


def parse_args():
    parser = argparse.ArgumentParser(description="Queue-aware length-aware proxy for vLLM serve")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8070)
    parser.add_argument("--backend_base_url", type=str, required=True)
    parser.add_argument("--policy", type=str, default="length_aware_v5", choices=["fifo", "length_aware_v5"])
    parser.add_argument("--short_threshold_chars", type=int, default=256)
    parser.add_argument("--max_consecutive_short", type=int, default=4)
    parser.add_argument("--max_active_requests", type=int, default=64)
    parser.add_argument("--max_queue_wait_sec", type=float, default=300.0)
    parser.add_argument("--arrival_window_size", type=int, default=256)
    parser.add_argument("--control_update_interval", type=int, default=64)
    parser.add_argument("--target_short_share_bonus", type=float, default=0.2)
    parser.add_argument("--min_short_share", type=float, default=0.5)
    parser.add_argument("--max_short_share", type=float, default=0.75)
    parser.add_argument("--long_head_wait_guard_ms", type=float, default=45000.0)
    parser.add_argument("--long_queue_len_guard", type=int, default=96)
    return parser.parse_args()


def main():
    args = parse_args()
    scheduler = LengthAwareScheduler(
        SchedulerConfig(
            policy=args.policy,
            short_threshold_chars=args.short_threshold_chars,
            max_consecutive_short=args.max_consecutive_short,
            max_active_requests=args.max_active_requests,
            max_queue_wait_sec=args.max_queue_wait_sec,
            arrival_window_size=args.arrival_window_size,
            control_update_interval=args.control_update_interval,
            target_short_share_bonus=args.target_short_share_bonus,
            min_short_share=args.min_short_share,
            max_short_share=args.max_short_share,
            long_head_wait_guard_ms=args.long_head_wait_guard_ms,
            long_queue_len_guard=args.long_queue_len_guard,
        )
    )
    handler = make_handler(scheduler, args.backend_base_url)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"[INFO] Length-aware proxy listening on http://{args.host}:{args.port}")
    print(f"[INFO] backend_base_url={args.backend_base_url}")
    print(f"[INFO] policy={args.policy}")
    print(f"[INFO] short_threshold_chars={args.short_threshold_chars}")
    print(f"[INFO] max_consecutive_short={args.max_consecutive_short}")
    print(f"[INFO] max_active_requests={args.max_active_requests}")
    print(f"[INFO] arrival_window_size={args.arrival_window_size}")
    print(f"[INFO] control_update_interval={args.control_update_interval}")
    print(f"[INFO] target_short_share_bonus={args.target_short_share_bonus}")
    print(f"[INFO] min_short_share={args.min_short_share}")
    print(f"[INFO] max_short_share={args.max_short_share}")
    print(f"[INFO] long_head_wait_guard_ms={args.long_head_wait_guard_ms}")
    print(f"[INFO] long_queue_len_guard={args.long_queue_len_guard}")
    server.serve_forever()


if __name__ == "__main__":
    main()
