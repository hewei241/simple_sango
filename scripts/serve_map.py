#!/usr/bin/env python3
"""本地地图服务：静态文件 + 将编辑结果写回 china-terrain-data.edit.js"""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDIT_JS = ROOT / "china-terrain-data.edit.js"


class MapHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/save-edit":
            self.send_error(404, "Not Found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            text = body.decode("utf-8")
            if "CHINA_TERRAIN_ROWS" not in text:
                raise ValueError("payload missing CHINA_TERRAIN_ROWS")
            EDIT_JS.write_text(text, encoding="utf-8")
            msg = f"saved {EDIT_JS.relative_to(ROOT)} ({len(text)} bytes)".encode("utf-8")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            print(f"[save-edit] wrote {EDIT_JS} ({len(text)} bytes)")
        except Exception as e:
            err = str(e).encode("utf-8")
            self.send_response(400)
            self._cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), MapHandler)
    print(f"Map server: http://127.0.0.1:{args.port}/index.html")
    print(f"Edit data:  {EDIT_JS}")
    print("POST /api/save-edit  -> overwrite china-terrain-data.edit.js")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
