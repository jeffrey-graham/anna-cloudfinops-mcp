#!/usr/bin/env python3
"""
Anna CloudFinOps & API Spend Guardian — Web App & MCP Tool Server
Supports both FastAPI (when installed) and zero-dependency Python stdlib HTTP serving.
"""

from __future__ import annotations
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.finops_engine import (
    DEFAULT_DEMO_RECORDS,
    MODEL_CATALOG,
    audit_spend_logs,
    detect_cost_anomalies,
    evaluate_budget_guardrails,
    recommend_routing_optimizations,
)
from src.mcp_tools import MCP_SERVER_INFO, MCP_TOOLS_SCHEMA, handle_mcp_jsonrpc

STATIC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))


def dispatch_http_request(
    method: str, path: str, body: Optional[Dict[str, Any]] = None
) -> Tuple[int, str, Any]:
    """
    Core HTTP request dispatcher used by both the stdlib server, FastAPI routes, and unit tests.
    Returns (status_code, content_type, body_payload).
    """
    clean_path = path.split("?")[0]

    if method == "GET" and clean_path in ("/", "/index.html"):
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                return 200, "text/html; charset=utf-8", f.read()
        return 404, "application/json", {"error": "static/index.html not found"}

    if method == "GET" and clean_path == "/api/health":
        return (
            200,
            "application/json",
            {
                "status": "ok",
                "app": MCP_SERVER_INFO,
                "mcp_tools_count": len(MCP_TOOLS_SCHEMA),
                "models_supported": list(MODEL_CATALOG.keys()),
            },
        )

    if method == "GET" and clean_path == "/api/demo-dataset":
        return (
            200,
            "application/json",
            {
                "window_days": 7.0,
                "monthly_budget_limit_usd": 15000.0,
                "records": DEFAULT_DEMO_RECORDS,
            },
        )

    if method == "POST" and clean_path == "/api/audit":
        payload = body or {}
        records = payload.get("records") or DEFAULT_DEMO_RECORDS
        window_days = float(payload.get("window_days", 7.0))
        budget_limit = float(payload.get("monthly_budget_limit_usd", 15000.0))

        audit = audit_spend_logs(records, window_days=window_days)
        anomalies = detect_cost_anomalies(records)
        optimization = recommend_routing_optimizations(records, window_days=window_days)
        guardrail = evaluate_budget_guardrails(
            audit["projected_monthly_usd"], monthly_budget_limit_usd=budget_limit
        )
        return (
            200,
            "application/json",
            {
                "audit": audit,
                "anomalies": anomalies,
                "optimization": optimization,
                "guardrail": guardrail,
            },
        )

    if method == "POST" and clean_path == "/mcp":
        rpc_res = handle_mcp_jsonrpc(body or {})
        return 200, "application/json", rpc_res

    return 404, "application/json", {"error": f"Route not found: {method} {clean_path}"}


# Optional FastAPI mounting if fastapi is installed in the runtime environment
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse

    app = FastAPI(
        title="Anna CloudFinOps & API Spend Guardian",
        version="1.0.0",
        description="Anna AI OS Marketplace Web App & MCP Tool Server for LLM/Cloud Spend Optimization",
    )

    @app.get("/", response_class=HTMLResponse)
    async def root_html() -> HTMLResponse:
        status, _, content = dispatch_http_request("GET", "/")
        return HTMLResponse(content=content, status_code=status)

    @app.get("/api/health")
    async def api_health() -> JSONResponse:
        status, _, content = dispatch_http_request("GET", "/api/health")
        return JSONResponse(content=content, status_code=status)

    @app.get("/api/demo-dataset")
    async def api_demo() -> JSONResponse:
        status, _, content = dispatch_http_request("GET", "/api/demo-dataset")
        return JSONResponse(content=content, status_code=status)

    @app.post("/api/audit")
    async def api_audit(request: Request) -> JSONResponse:
        body = await request.json()
        status, _, content = dispatch_http_request("POST", "/api/audit", body)
        return JSONResponse(content=content, status_code=status)

    @app.post("/mcp")
    async def mcp_endpoint(request: Request) -> JSONResponse:
        body = await request.json()
        status, _, content = dispatch_http_request("POST", "/mcp", body)
        return JSONResponse(content=content, status_code=status)

except ImportError:
    app = None


class AnnaFinOpsHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        status, ctype, payload = dispatch_http_request("GET", self.path)
        self._send(status, ctype, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            body = {}
        status, ctype, payload = dispatch_http_request("POST", self.path, body)
        self._send(status, ctype, payload)

    def _send(self, status: int, ctype: str, payload: Any) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(payload, str):
            self.wfile.write(payload.encode("utf-8"))
        else:
            self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8090) -> None:
    httpd = ThreadingHTTPServer((host, port), AnnaFinOpsHTTPHandler)
    print(f"[+] Anna CloudFinOps & API Spend Guardian running on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    run_server(port=port)
