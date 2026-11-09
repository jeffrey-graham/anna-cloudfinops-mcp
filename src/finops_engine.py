"""
Anna CloudFinOps & API Spend Guardian — Core FinOps Analytics & Routing Engine
Built for the Anna AI App Builder Program (https://dorahacks.io/hackathon/2349 | anna.partners)
"""

from __future__ import annotations
import math
import statistics
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    provider: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    cached_input_cost_per_1m: float
    quality_tier: int  # 1 = lightweight/fast, 2 = balanced, 3 = frontier reasoning
    latency_p95_ms: int
    context_window: int


MODEL_CATALOG: Dict[str, ModelSpec] = {
    "gpt-4o": ModelSpec("gpt-4o", "OpenAI", 2.50, 10.00, 1.25, 3, 1450, 128000),
    "gpt-4o-mini": ModelSpec("gpt-4o-mini", "OpenAI", 0.15, 0.60, 0.075, 1, 480, 128000),
    "o3-mini": ModelSpec("o3-mini", "OpenAI", 1.10, 4.40, 0.55, 3, 2100, 200000),
    "claude-3-7-sonnet": ModelSpec("claude-3-7-sonnet", "Anthropic", 3.00, 15.00, 0.30, 3, 1650, 200000),
    "claude-3-5-haiku": ModelSpec("claude-3-5-haiku", "Anthropic", 0.80, 4.00, 0.08, 2, 520, 200000),
    "gemini-2.5-pro": ModelSpec("gemini-2.5-pro", "Google", 1.25, 5.00, 0.31, 3, 1300, 1000000),
    "gemini-2.5-flash": ModelSpec("gemini-2.5-flash", "Google", 0.10, 0.40, 0.025, 1, 390, 1000000),
    "deepseek-v3": ModelSpec("deepseek-v3", "DeepSeek", 0.27, 1.10, 0.07, 2, 850, 128000),
}

# Recommended target model per task category & minimum required quality tier
TASK_ROUTING_RULES: Dict[str, Dict[str, Any]] = {
    "classification": {"min_tier": 1, "preferred_model": "gemini-2.5-flash"},
    "extraction": {"min_tier": 1, "preferred_model": "gpt-4o-mini"},
    "summarization": {"min_tier": 1, "preferred_model": "gemini-2.5-flash"},
    "customer_support": {"min_tier": 2, "preferred_model": "claude-3-5-haiku"},
    "code_generation": {"min_tier": 2, "preferred_model": "deepseek-v3"},
    "deep_reasoning": {"min_tier": 3, "preferred_model": "o3-mini"},
}


def compute_record_cost(record: Dict[str, Any]) -> float:
    """Compute exact USD cost for a single API/LLM usage log entry."""
    model_id = str(record.get("model", "gpt-4o"))
    spec = MODEL_CATALOG.get(model_id, MODEL_CATALOG["gpt-4o"])

    input_tokens = max(0, int(record.get("input_tokens", 0)))
    cached_tokens = max(0, min(input_tokens, int(record.get("cached_input_tokens", 0))))
    uncached_input_tokens = input_tokens - cached_tokens
    output_tokens = max(0, int(record.get("output_tokens", 0)))
    cloud_infra_usd = float(record.get("cloud_infra_usd", 0.0))

    llm_cost = (
        (uncached_input_tokens / 1_000_000.0) * spec.input_cost_per_1m
        + (cached_tokens / 1_000_000.0) * spec.cached_input_cost_per_1m
        + (output_tokens / 1_000_000.0) * spec.output_cost_per_1m
    )
    return round(llm_cost + cloud_infra_usd, 6)


def audit_spend_logs(records: List[Dict[str, Any]], window_days: float = 7.0) -> Dict[str, Any]:
    """
    Audit a batch of LLM/API and cloud spend telemetry logs.
    Returns total cost, projected 30-day run-rate, breakdown by model/team/task, and cache efficiency.
    """
    if not records:
        return {
            "total_cost_usd": 0.0,
            "projected_monthly_usd": 0.0,
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_cached_tokens": 0,
            "total_output_tokens": 0,
            "cache_hit_ratio": 0.0,
            "by_model": {},
            "by_team": {},
            "by_task": {},
        }

    total_cost = 0.0
    total_requests = 0
    total_input = 0
    total_cached = 0
    total_output = 0
    by_model: Dict[str, float] = {}
    by_team: Dict[str, float] = {}
    by_task: Dict[str, float] = {}

    for rec in records:
        cost = compute_record_cost(rec)
        reqs = max(1, int(rec.get("requests", 1)))
        inp = max(0, int(rec.get("input_tokens", 0)))
        cached = max(0, min(inp, int(rec.get("cached_input_tokens", 0))))
        out = max(0, int(rec.get("output_tokens", 0)))

        total_cost += cost
        total_requests += reqs
        total_input += inp
        total_cached += cached
        total_output += out

        model = str(rec.get("model", "gpt-4o"))
        team = str(rec.get("team", "default"))
        task = str(rec.get("task_type", "general"))

        by_model[model] = round(by_model.get(model, 0.0) + cost, 4)
        by_team[team] = round(by_team.get(team, 0.0) + cost, 4)
        by_task[task] = round(by_task.get(task, 0.0) + cost, 4)

    effective_days = max(0.1, float(window_days))
    projected_monthly = (total_cost / effective_days) * 30.0
    cache_hit_ratio = (total_cached / total_input) if total_input > 0 else 0.0

    return {
        "total_cost_usd": round(total_cost, 4),
        "projected_monthly_usd": round(projected_monthly, 2),
        "total_requests": total_requests,
        "total_input_tokens": total_input,
        "total_cached_tokens": total_cached,
        "total_output_tokens": total_output,
        "cache_hit_ratio": round(cache_hit_ratio, 4),
        "by_model": by_model,
        "by_team": by_team,
        "by_task": by_task,
    }


def detect_cost_anomalies(
    records: List[Dict[str, Any]], z_threshold: float = 1.8
) -> List[Dict[str, Any]]:
    """
    Detect statistical spend spikes (Z-score), runaway retry loops, and uncached large context prompts.
    """
    if not records:
        return []

    costs = [compute_record_cost(r) for r in records]
    mean_cost = statistics.mean(costs)
    stdev_cost = statistics.pstdev(costs) if len(costs) > 1 else 0.0

    anomalies: List[Dict[str, Any]] = []

    for idx, rec in enumerate(records):
        cost = costs[idx]
        reqs = max(1, int(rec.get("requests", 1)))
        inp = max(0, int(rec.get("input_tokens", 0)))
        cached = max(0, int(rec.get("cached_input_tokens", 0)))
        retry_rate = float(rec.get("retry_rate", 0.0))
        endpoint = str(rec.get("endpoint", f"record-{idx}"))
        model = str(rec.get("model", "gpt-4o"))

        reasons: List[str] = []
        severity = "normal"

        z_score = ((cost - mean_cost) / stdev_cost) if stdev_cost > 1e-9 else 0.0
        if z_score >= z_threshold and cost > 5.0:
            reasons.append(f"Spend Z-score spike (z={z_score:.2f}, ${cost:.2f} vs mean ${mean_cost:.2f})")
            severity = "critical" if z_score >= 2.3 else "high"

        if retry_rate >= 0.25:
            reasons.append(f"Runaway agent retry loop detected (retry_rate={retry_rate * 100:.1f}%)")
            severity = "critical"

        avg_input_per_req = inp / reqs
        cache_ratio = (cached / inp) if inp > 0 else 1.0
        if avg_input_per_req >= 12_000 and cache_ratio < 0.15:
            reasons.append(
                f"Uncached heavy system prompt ({int(avg_input_per_req):,} input tok/req with {cache_ratio * 100:.1f}% cache hit)"
            )
            if severity == "normal":
                severity = "high"

        if reasons:
            anomalies.append(
                {
                    "record_index": idx,
                    "endpoint": endpoint,
                    "team": str(rec.get("team", "default")),
                    "model": model,
                    "cost_usd": round(cost, 4),
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "reasons": reasons,
                }
            )

    return anomalies


def recommend_routing_optimizations(
    records: List[Dict[str, Any]], window_days: float = 7.0
) -> Dict[str, Any]:
    """
    Evaluate each workload against TASK_ROUTING_RULES and prompt caching best practices.
    Returns itemized recommendations, projected monthly savings, and an Anna AI OS routing policy.
    """
    recommendations: List[Dict[str, Any]] = []
    total_current_cost = 0.0
    total_optimized_cost = 0.0
    routing_policy_rules: List[Dict[str, Any]] = []

    for idx, rec in enumerate(records):
        current_model = str(rec.get("model", "gpt-4o"))
        task_type = str(rec.get("task_type", "general"))
        endpoint = str(rec.get("endpoint", f"workload-{idx}"))
        inp = max(0, int(rec.get("input_tokens", 0)))
        cached = max(0, int(rec.get("cached_input_tokens", 0)))
        out = max(0, int(rec.get("output_tokens", 0)))
        retry_rate = float(rec.get("retry_rate", 0.0))

        cur_cost = compute_record_cost(rec)
        total_current_cost += cur_cost

        rule = TASK_ROUTING_RULES.get(task_type)
        target_model = rule["preferred_model"] if rule else current_model
        target_spec = MODEL_CATALOG.get(target_model, MODEL_CATALOG.get(current_model, MODEL_CATALOG["gpt-4o"]))

        # Simulate prompt caching (75% of input tokens cached for repetitive endpoints) + circuit breaker on retries
        effective_scale = 1.0 - min(0.5, max(0.0, retry_rate - 0.05))
        scaled_inp = int(inp * effective_scale)
        scaled_out = int(out * effective_scale)
        target_cached = max(cached, int(scaled_inp * 0.70)) if scaled_inp >= 5_000 else cached

        opt_rec = {
            **rec,
            "model": target_model,
            "input_tokens": scaled_inp,
            "cached_input_tokens": min(scaled_inp, target_cached),
            "output_tokens": scaled_out,
        }
        opt_cost = min(cur_cost, compute_record_cost(opt_rec))
        total_optimized_cost += opt_cost

        savings_usd = max(0.0, cur_cost - opt_cost)
        savings_pct = ((savings_usd / cur_cost) * 100.0) if cur_cost > 0 else 0.0

        if savings_usd > 0.01:
            actions = []
            if target_model != current_model:
                actions.append(f"Route '{task_type}' from {current_model} -> {target_model}")
            if target_cached > cached:
                actions.append("Enable prefix prompt caching (target 70% cached input tokens)")
            if retry_rate >= 0.15:
                actions.append("Enforce exponential backoff & max-2 retry circuit breaker")

            recommendations.append(
                {
                    "endpoint": endpoint,
                    "team": str(rec.get("team", "default")),
                    "task_type": task_type,
                    "current_model": current_model,
                    "recommended_model": target_model,
                    "current_cost_usd": round(cur_cost, 4),
                    "optimized_cost_usd": round(opt_cost, 4),
                    "window_savings_usd": round(savings_usd, 4),
                    "savings_percent": round(savings_pct, 2),
                    "latency_delta_ms": target_spec.latency_p95_ms
                    - MODEL_CATALOG.get(current_model, target_spec).latency_p95_ms,
                    "actions": actions,
                }
            )
            routing_policy_rules.append(
                {
                    "match": {"endpoint": endpoint, "task_type": task_type},
                    "route_to": target_model,
                    "enable_prompt_caching": True,
                    "max_retries": 2,
                }
            )

    scale_to_month = 30.0 / max(0.1, float(window_days))
    monthly_current = total_current_cost * scale_to_month
    monthly_optimized = total_optimized_cost * scale_to_month
    monthly_savings = max(0.0, monthly_current - monthly_optimized)
    overall_pct = ((monthly_savings / monthly_current) * 100.0) if monthly_current > 0 else 0.0

    return {
        "window_current_cost_usd": round(total_current_cost, 4),
        "window_optimized_cost_usd": round(total_optimized_cost, 4),
        "projected_monthly_current_usd": round(monthly_current, 2),
        "projected_monthly_optimized_usd": round(monthly_optimized, 2),
        "projected_monthly_savings_usd": round(monthly_savings, 2),
        "overall_savings_percent": round(overall_pct, 2),
        "recommendations": recommendations,
        "anna_routing_policy": {
            "schema_version": "anna.finops.v1",
            "auto_downgrade_on_budget_pressure": True,
            "rules": routing_policy_rules,
        },
    }


def evaluate_budget_guardrails(
    projected_monthly_usd: float,
    monthly_budget_limit_usd: float,
) -> Dict[str, Any]:
    """
    Evaluate workspace spend against Anna AI OS FinOps guardrail thresholds:
      - < 75%: HEALTHY
      - 75% - 89.9%: WARNING (alert workspace owners + enable aggressive prompt caching)
      - 90% - 99.9%: THROTTLE_TIER (auto-downgrade non-reasoning routes to tier-1 flash/mini models)
      - >= 100%: CIRCUIT_BREAKER (block unapproved tier-3 calls & enforce hard rate caps)
    """
    limit = max(1.0, float(monthly_budget_limit_usd))
    utilization = (projected_monthly_usd / limit) * 100.0

    if utilization >= 100.0:
        status = "CIRCUIT_BREAKER"
        action = "Pause non-critical Tier-3 frontier model calls and force Tier-1 fallback models immediately."
    elif utilization >= 90.0:
        status = "THROTTLE_TIER"
        action = "Auto-downgrade classification, summarization, and extraction routes to gemini-2.5-flash / gpt-4o-mini."
    elif utilization >= 75.0:
        status = "WARNING"
        action = "Notify Anna AI OS workspace admin and enforce mandatory prompt prefix caching."
    else:
        status = "HEALTHY"
        action = "Spend within target guardrail envelope."

    return {
        "status": status,
        "utilization_percent": round(utilization, 2),
        "projected_monthly_usd": round(projected_monthly_usd, 2),
        "monthly_budget_limit_usd": round(limit, 2),
        "recommended_action": action,
    }


DEFAULT_DEMO_RECORDS: List[Dict[str, Any]] = [
    {
        "endpoint": "/v1/agent/intent-classifier",
        "team": "core-router",
        "task_type": "classification",
        "model": "claude-3-7-sonnet",
        "requests": 42000,
        "input_tokens": 588_000_000,
        "cached_input_tokens": 20_000_000,
        "output_tokens": 18_500_000,
        "retry_rate": 0.04,
        "cloud_infra_usd": 45.0,
    },
    {
        "endpoint": "/v1/agent/invoice-extractor",
        "team": "finance-ops",
        "task_type": "extraction",
        "model": "gpt-4o",
        "requests": 19500,
        "input_tokens": 390_000_000,
        "cached_input_tokens": 15_000_000,
        "output_tokens": 29_000_000,
        "retry_rate": 0.34,
        "cloud_infra_usd": 32.0,
    },
    {
        "endpoint": "/v1/agent/meeting-digest",
        "team": "productivity",
        "task_type": "summarization",
        "model": "gpt-4o",
        "requests": 12000,
        "input_tokens": 310_000_000,
        "cached_input_tokens": 10_000_000,
        "output_tokens": 24_000_000,
        "retry_rate": 0.03,
        "cloud_infra_usd": 18.0,
    },
    {
        "endpoint": "/v1/agent/pr-code-synthesizer",
        "team": "dev-platform",
        "task_type": "code_generation",
        "model": "claude-3-7-sonnet",
        "requests": 8400,
        "input_tokens": 210_000_000,
        "cached_input_tokens": 40_000_000,
        "output_tokens": 36_000_000,
        "retry_rate": 0.06,
        "cloud_infra_usd": 28.0,
    },
    {
        "endpoint": "/v1/agent/quant-risk-solver",
        "team": "risk-engine",
        "task_type": "deep_reasoning",
        "model": "o3-mini",
        "requests": 3200,
        "input_tokens": 64_000_000,
        "cached_input_tokens": 32_000_000,
        "output_tokens": 16_000_000,
        "retry_rate": 0.02,
        "cloud_infra_usd": 15.0,
    },
]
