import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.finops_engine import (
    DEFAULT_DEMO_RECORDS,
    audit_spend_logs,
    compute_record_cost,
    detect_cost_anomalies,
    evaluate_budget_guardrails,
    recommend_routing_optimizations,
)
from src.mcp_tools import handle_mcp_jsonrpc
from src.server import dispatch_http_request


class TestAnnaCloudFinOps(unittest.TestCase):
    def test_1_compute_record_cost_and_audit_spend(self) -> None:
        audit = audit_spend_logs(DEFAULT_DEMO_RECORDS, window_days=7.0)
        self.assertGreater(audit["total_cost_usd"], 4000.0)
        self.assertGreater(audit["projected_monthly_usd"], 18000.0)
        self.assertEqual(audit["total_requests"], 85100)
        self.assertIn("claude-3-7-sonnet", audit["by_model"])
        self.assertIn("gpt-4o", audit["by_model"])

    def test_2_detect_cost_anomalies_flags_retry_loop_and_uncached_prompts(self) -> None:
        anomalies = detect_cost_anomalies(DEFAULT_DEMO_RECORDS, z_threshold=1.5)
        self.assertGreaterEqual(len(anomalies), 3)
        endpoints = {a["endpoint"] for a in anomalies}
        self.assertIn("/v1/agent/invoice-extractor", endpoints)
        self.assertIn("/v1/agent/intent-classifier", endpoints)

    def test_3_recommend_routing_optimizations_saves_over_75_percent(self) -> None:
        opt = recommend_routing_optimizations(DEFAULT_DEMO_RECORDS, window_days=7.0)
        self.assertGreater(opt["projected_monthly_savings_usd"], 14000.0)
        self.assertGreater(opt["overall_savings_percent"], 75.0)
        self.assertEqual(opt["anna_routing_policy"]["schema_version"], "anna.finops.v1")
        self.assertGreaterEqual(len(opt["anna_routing_policy"]["rules"]), 4)

    def test_4_budget_guardrails_thresholds(self) -> None:
        cb = evaluate_budget_guardrails(18897.86, 15000.0)
        self.assertEqual(cb["status"], "CIRCUIT_BREAKER")

        th = evaluate_budget_guardrails(13800.0, 15000.0)
        self.assertEqual(th["status"], "THROTTLE_TIER")

        ok = evaluate_budget_guardrails(5000.0, 15000.0)
        self.assertEqual(ok["status"], "HEALTHY")

    def test_5_mcp_jsonrpc_protocol_lifecycle(self) -> None:
        init_res = handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(init_res["result"]["protocolVersion"], "2024-11-05")

        list_res = handle_mcp_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in list_res["result"]["tools"]]
        self.assertEqual(
            tool_names,
            [
                "finops_audit_spend",
                "finops_detect_anomalies",
                "finops_optimize_routing",
                "finops_evaluate_budget_policy",
            ],
        )

        call_res = handle_mcp_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "finops_optimize_routing", "arguments": {"window_days": 7.0}},
            }
        )
        self.assertFalse(call_res["result"]["isError"])
        self.assertGreater(
            call_res["result"]["structuredContent"]["projected_monthly_savings_usd"], 14000.0
        )

    def test_6_http_dispatcher_endpoints(self) -> None:
        status, ctype, html = dispatch_http_request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Anna CloudFinOps", html)

        status, _, health = dispatch_http_request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["mcp_tools_count"], 4)

        status, _, report = dispatch_http_request(
            "POST", "/api/audit", {"window_days": 7.0, "monthly_budget_limit_usd": 15000.0}
        )
        self.assertEqual(status, 200)
        self.assertIn("audit", report)
        self.assertIn("optimization", report)
        self.assertEqual(report["guardrail"]["status"], "CIRCUIT_BREAKER")


if __name__ == "__main__":
    unittest.main()
