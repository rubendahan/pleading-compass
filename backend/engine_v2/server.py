"""Tiny HTTP endpoint — ``POST /analyze`` → AppData JSON.

The frontend's re-analyze seam (ENGINE_URL) posts ``{pleading, bundle}`` (or
``{propositions, bundle}``) and gets back ``to_appdata(...)``. Stdlib only.
Host/port from ENGINE_HOST / ENGINE_PORT (default 127.0.0.1:8000).
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import ingest, pipeline


def build_appdata(body: dict) -> dict:
    offline = bool(body.get("offline", True))
    meta = body.get("meta")
    chronology = body.get("chronology")
    bundle = ingest.coerce_bundle(body.get("bundle", {}))

    if "propositions" in body and body["propositions"] is not None:
        propositions = body["propositions"]
    elif "pleading" in body and body["pleading"] is not None:
        pl = body["pleading"]
        # a pleading document given inline: fold it into the bundle, derive props
        one = ingest.coerce_bundle({pl.get("id", "02"): {
            "paras": pl.get("paras", []),
            "doc_type": pl.get("doc_type", "pleading"),
            "party": pl.get("party", "claimant"),
            "title": pl.get("title", "Particulars of Claim"),
            "date": pl.get("date"),
        }})
        pdoc = one.docs[0]
        if bundle.get(pdoc.id) is None:
            bundle.docs.append(pdoc)
            bundle.docs.sort(key=lambda d: d.id)
        propositions = ingest.coerce_propositions(pdoc, bundle)
    else:
        raise ValueError("body needs 'propositions' or 'pleading'")

    return pipeline.to_appdata(propositions, bundle, offline=offline,
                              meta=meta, chronology=chronology)


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/analyze":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            appdata = build_appdata(body)
        except Exception as exc:  # surface a clean error to the client
            self._send(400, {"error": str(exc)})
            return
        self._send(200, appdata)

    def log_message(self, *args) -> None:  # quiet by default
        pass


def serve(host: str | None = None, port: int | None = None) -> None:  # pragma: no cover
    host = host or os.getenv("ENGINE_HOST", "127.0.0.1")
    port = port or int(os.getenv("ENGINE_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"engine_v2 server on http://{host}:{port}/analyze")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":  # pragma: no cover
    serve()
