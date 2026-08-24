from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser

from .dashboard import render_dashboard
from .db import connect
from .start_flow import evaluate_start


def make_handler(db_path: Path, evidence_dir: Path):
    class DashboardHandler(BaseHTTPRequestHandler):
        def _send(self, body: str, status: int = 200) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            if self.path != "/":
                self._send("Bulunamadı", 404)
                return
            self._send(render_dashboard())

        def do_POST(self) -> None:
            if self.path != "/start":
                self._send("Bulunamadı", 404)
                return
            conn = connect(db_path)
            try:
                result = evaluate_start(conn, evidence_dir)
            finally:
                conn.close()
            self._send(render_dashboard(result))

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return DashboardHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="db/real_evidence.db")
    parser.add_argument("--evidence", default="evidence/real")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    address = ("127.0.0.1", args.port)
    server = ThreadingHTTPServer(
        address, make_handler(Path(args.db).resolve(), Path(args.evidence).resolve())
    )
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Serhat AI Publisher hazır: {url}")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
