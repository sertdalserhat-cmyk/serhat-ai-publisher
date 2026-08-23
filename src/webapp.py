from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser
from urllib.parse import parse_qs

from .blueprint import build_blueprint_preview
from .dashboard import render_blueprint, render_dashboard, render_review
from .db import connect
from .opportunity import set_status
from .review import load_review
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
            if self.path == "/":
                self._send(render_dashboard())
                return
            if self.path == "/review":
                conn = connect(db_path)
                try:
                    self._send(render_review(load_review(conn)))
                finally:
                    conn.close()
                return
            if self.path == "/blueprint":
                conn = connect(db_path)
                try:
                    preview = build_blueprint_preview(load_review(conn))
                    self._send(render_blueprint(preview))
                finally:
                    conn.close()
                return
            else:
                self._send("Bulunamadı", 404)

        def do_POST(self) -> None:
            if self.path == "/start":
                conn = connect(db_path)
                try:
                    result = evaluate_start(conn, evidence_dir)
                finally:
                    conn.close()
                self._send(render_dashboard(result))
                return
            if self.path == "/decision":
                length = int(self.headers.get("Content-Length", "0"))
                form = parse_qs(self.rfile.read(length).decode("utf-8"))
                status = form.get("status", [""])[0]
                rationale = form.get("rationale", [""])[0]
                confirmed = form.get("confirm", [""])[0] == "YES"
                conn = connect(db_path)
                try:
                    review = load_review(conn)
                    if not confirmed:
                        raise ValueError("Karar için açık onay kutusu zorunludur")
                    set_status(conn, review.id, status, rationale)
                    review = load_review(conn, review.id)
                    self._send(render_review(review, "Kararın değiştirilemez günlüğe kaydedildi."))
                except ValueError as exc:
                    self._send(render_review(load_review(conn), str(exc)), 400)
                finally:
                    conn.close()
                return
            else:
                self._send("Bulunamadı", 404)

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
