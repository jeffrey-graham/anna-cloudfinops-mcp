"""
Anna CloudFinOps & API Spend Guardian — Model Context Protocol (MCP 2024-11-05) Server Tools
Exposes structured FinOps tools & resources for Anna AI OS agents (anna.partners).
"""

from __future__ import annotations
import json
from typing import Any, Dict, List

from src.finops_engine import (
    DEFAULT_DEMO_RECORDS,
    MODEL_CATALOG,
    audit_spend_logs,
    detect_cost_anomalies,
    evaluate_budget_guardrails,
    recommend_routing_optimizations,
)

MCP_SERVER_INFO = {
    "name": "anna-cloudfinops-guardian",
    "version": "1.0.0",
    "vendor": "Anna AI OS Partner Ecosystem",
    "protocolVersion": "2024-11-05",
}

MCP_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "finops_audit_spend",
        "description": "Audit LLM/API and cloud spend telemetry logs across providers, teams, and task types, returning total cost, 30-day run-rate, and prompt cache hit ratio.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "List of usage telemetry records (optional; uses enterprise demo dataset if omitted).",
                },
                "window_days": {
                    "type": "number",
                    "default": 7.0,
                    "description": "Observation window in days represented by the records.",
                },
            },
        },
    },
    {
        "name": "finops_detect_anomalies",
        "description": "Detect Z-score cost spikes, runaway agent retry loops, and uncached heavy system prompts across LLM/API endpoints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "List of usage telemetry records (optional; uses enterprise demo dataset if omitted).",
                },
                "z_threshold": {
                    "type": "number",
                    "default": 1.8,
                    "description": "Z-score threshold for flagging statistical spend anomalies.",
                },
            },
        },
    },
    {
        "name": "finops_optimize_routing",
        "description": "Generate model-routing and prompt-caching optimizations with quantified monthly USD savings and an executable Anna AI OS routing policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "List of usage telemetry records (optional; uses enterprise demo dataset if omitted).",
                },
                "window_days": {
                    "type": "number",
                    "default": 7.0,
                },
            },
        },
    },
    {
        "name": "finops_evaluate_budget_policy",
        "description": "Evaluate projected monthly workspace spend against Anna AI OS budget guardrails (HEALTHY, WARNING, THROTTLE_TIER, CIRCUIT_BREAKER).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projected_monthly_usd": {"type": "number"},
                "monthly_budget_limit_usd": {"type": "number", "default": 15000.0},
            },
            "required": ["projected_monthly_usd"],
        },
    },
]


def handle_mcp_jsonrpc(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a JSON-RPC 2.0 Model Context Protocol (MCP) request and return a standards-compliant response.
    """
    req_id = request.get("id", 1)
    method = request.get("method", "")
    params = request.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": MCP_SERVER_INFO,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
            },
        }

    if method in ("notifications/initialized", "initialized", "ping"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {},
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS_SCHEMA},
        }

    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": [
                    {
                        "uri": "anna://finops/model-pricing-catalog",
                        "name": "LLM Model Pricing & Latency Catalog (2026)",
                        "mimeType": "application/json",
                    }
                ]
            },
        }

    if method == "resources/read":
        uri = params.get("uri", "")
        if uri == "anna://finops/model-pricing-catalog":
            catalog_dict = {k: v.__dict__ for k, v in MODEL_CATALOG.items()}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(catalog_dict, indent=2),
                        }
                    ]
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": f"Unknown resource URI: {uri}"},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            records = args.get("records") or DEFAULT_DEMO_RECORDS
            window_days = float(args.get("window_days", 7.0))
            if window_days <= 0:
                raise ValueError("window_days must be > 0")

            if tool_name == "finops_audit_spend":
                payload = audit_spend_logs(records, window_days=window_days)
            elif tool_name == "finops_detect_anomalies":
                z_thresh = float(args.get("z_threshold", 1.8))
                payload = {"anomalies": detect_cost_anomalies(records, z_threshold=z_thresh)}
            elif tool_name == "finops_optimize_routing":
                payload = recommend_routing_optimizations(records, window_days=window_days)
            elif tool_name == "finops_evaluate_budget_policy":
                proj = float(args.get("projected_monthly_usd", 18000.0))
                limit = float(args.get("monthly_budget_limit_usd", 15000.0))
                payload = evaluate_budget_guardrails(proj, limit)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown MCP tool: {tool_name}"},
                }
        except (ValueError, TypeError, KeyError) as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Tool execution error: {exc}"}],
                    "isError": True,
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(payload, indent=2),
                    }
                ],
                "structuredContent": payload,
                "isError": False,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
