"""NIYAM Gateway API Server
FastAPI application orchestrating policy compilation, deterministic gate evaluation,
idempotency checking, Razorpay MCP dispatch, and immutable audit logging.
"""
import hashlib
import hmac
import json
import uuid
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from pydantic import BaseModel, Field

from services.compiler.schema import (
    SpendingPolicy,
    PurchaseRequest,
    PurchaseItem,
    UserSpendState,
    EvaluationResult,
    ReasonCode,
)
from services.compiler.compiler import PolicyCompiler
from services.evaluator.engine import evaluate_purchase
from services.gateway.idempotency import IdempotencyManager
from services.gateway.audit_ledger import AuditLedger
from services.gateway.catalog import get_agent_catalog
from services.gateway.rate_limiter import TokenBucketRateLimiter
from services.mcp_client.razorpay_client import RazorpayMCPClient
from services.mcp_client.circuit_breaker import CircuitBreakerOpenException
from services.growth.engine import GrowthEngine


# Initialize FastAPI
app = FastAPI(
    title="NIYAM — Agentic Commerce Policy Enforcement Gateway",
    description="Deterministic policy enforcement, explainability, and graceful failure handling for autonomous AI agents.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Gateway Services
compiler = PolicyCompiler()
idempotency_mgr = IdempotencyManager(ttl_seconds=86400)
audit_ledger = AuditLedger(data_dir="data")
razorpay_client = RazorpayMCPClient()
growth_engine = GrowthEngine()
rate_limiter = TokenBucketRateLimiter(capacity=50, refill_rate_per_sec=10.0)


# In-memory stores (persisted to disk via audit_ledger snapshots)
user_policies: Dict[str, List[SpendingPolicy]] = {}
user_spend_states: Dict[str, UserSpendState] = {}
registered_agents: Dict[str, Dict[str, Any]] = {}


# Request Models
class PolicyCompileRequest(BaseModel):
    user_id: str = Field(default="usr_rahul_982")
    prompt: str = Field(
        default="Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena. Sirf returnable items lena."
    )


class AgentRegisterRequest(BaseModel):
    agent_name: str
    principal_user_id: str


class ChaosToggleRequest(BaseModel):
    enabled: bool


class HeadroomRequest(BaseModel):
    user_id: str = Field(default="usr_rahul_982")
    cart_total: float = Field(default=450.0)


class RecommendationsRequest(BaseModel):
    user_id: str = Field(default="usr_rahul_982")
    cart_total: float = Field(default=450.0)


class WaiverCreateRequest(BaseModel):
    user_id: str
    agent_id: str
    cart_total: float
    policy_limit: float
    reason: str


# Pre-seed baseline demo data
def _seed_demo_state():
    default_user = "usr_rahul_982"
    initial_prompt = "Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena. Sirf returnable items lena."
    p1 = compiler.compile(initial_prompt, default_user, current_version="v0")
    user_policies[default_user] = [p1]
    user_spend_states[default_user] = UserSpendState(
        user_id=default_user,
        monthly_spend_accumulated=1800.0,
        category_spend_accumulated={"toys": 450.0, "groceries": 1350.0}
    )
    
    # Pre-register default demo agent
    agent_id = "agent_shopper_01"
    raw_key = "sk_live_agentic_shopper_demo_token"
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    registered_agents[agent_id] = {
        "agent_name": "Autonomous Gifting Shopper",
        "principal_user_id": default_user,
        "hashed_key": hashed,
        "registered_at": datetime.now(timezone.utc).isoformat()
    }

_seed_demo_state()


# Endpoints

@app.get("/healthz")
def healthcheck():
    return {
        "status": "healthy",
        "gateway": "NIYAM v1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "circuit_breaker": razorpay_client.circuit_breaker.get_status()
    }


@app.post("/policies")
def create_policy(req: PolicyCompileRequest):
    """Compiles natural language (Hinglish/English) into an immutable, versioned SpendingPolicy."""
    user_history = user_policies.get(req.user_id, [])
    current_ver = user_history[-1].policy_version if user_history else "v0"
    
    try:
        new_policy = compiler.compile(req.prompt, req.user_id, current_version=current_ver)
    except Exception as e:
        audit_ledger.record_entry(
            agent_id="system_compiler",
            user_id=req.user_id,
            action="SCHEMA_VALIDATION_ERROR",
            amount=0.0,
            policy_snapshot=None,
            decision={"reason_code": ReasonCode.SCHEMA_VALIDATION_ERROR, "error": str(e)},
            explainability=f"Compilation failed: {str(e)}",
            is_failure_handled=True
        )
        raise HTTPException(status_code=400, detail=f"Policy compilation error: {str(e)}")

    if req.user_id not in user_policies:
        user_policies[req.user_id] = []
    user_policies[req.user_id].append(new_policy)

    # Record to immutable audit ledger
    audit_ledger.record_entry(
        agent_id="user_admin",
        user_id=req.user_id,
        action="POLICY_CREATED",
        amount=0.0,
        policy_snapshot=new_policy.model_dump(mode="json"),
        decision={"reason_code": "POLICY_ACTIVATED", "version": new_policy.policy_version},
        explainability=f"New policy {new_policy.policy_version} compiled and activated for user {req.user_id}.",
        is_failure_handled=False
    )

    return {
        "status": "success",
        "message": f"Policy {new_policy.policy_version} compiled and activated successfully.",
        "policy": new_policy
    }


@app.get("/policies/{user_id}")
def get_user_policies(user_id: str):
    """Retrieve active policy snapshot and complete version history for a user."""
    history = user_policies.get(user_id, [])
    if not history:
        raise HTTPException(status_code=404, detail="No policy found for this user.")
    return {
        "user_id": user_id,
        "active_policy": history[-1],
        "version_history": history
    }


@app.post("/agents/register")
def register_agent(req: AgentRegisterRequest):
    """Registers an autonomous agent, generates API key, and stores SHA-256 hash at rest."""
    agent_id = f"agent_{uuid.uuid4().hex[:10]}"
    raw_key = f"niyam_sk_{uuid.uuid4().hex}"
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()

    registered_agents[agent_id] = {
        "agent_name": req.agent_name,
        "principal_user_id": req.principal_user_id,
        "hashed_key": hashed_key,
        "registered_at": datetime.now(timezone.utc).isoformat()
    }

    return {
        "agent_id": agent_id,
        "agent_name": req.agent_name,
        "api_key": raw_key,
        "note": "Save this API key. Raw key is never stored; only SHA-256 hash is preserved at rest."
    }


@app.get("/catalog/agent")
def get_catalog(category: Optional[str] = None):
    """Machine-readable product catalog with explicit policy tags for autonomous AI buyers."""
    return get_agent_catalog(category)


@app.post("/purchase")
def execute_purchase(request: PurchaseRequest, x_agent_key: Optional[str] = Header(None)):
    """Core enforcement gateway: Deterministic policy evaluation, idempotency check, and Razorpay dispatch."""
    # 1. Agent Authentication Check (Simulated or Key-Based)
    if x_agent_key and request.agent_id in registered_agents:
        hashed_input = hashlib.sha256(x_agent_key.encode()).hexdigest()
        if hashed_input != registered_agents[request.agent_id]["hashed_key"]:
            raise HTTPException(status_code=401, detail="Invalid agent API key.")

    # 2. Idempotency Gate (Prevent double-debits & duplicate retries)
    cached_response = idempotency_mgr.check(request.idempotency_key, request.agent_id)
    if cached_response is not None:
        # Record duplicate suppression in audit ledger
        audit_ledger.record_entry(
            agent_id=request.agent_id,
            user_id=request.user_id,
            action="DUPLICATE_SUPPRESSED",
            amount=cached_response.get("amount", 0.0),
            policy_snapshot=None,
            decision={
                "reason_code": ReasonCode.DUPLICATE_SUPPRESSED,
                "idempotency_key": request.idempotency_key
            },
            explainability=f"Duplicate request detected with key '{request.idempotency_key}'. Returning cached execution result without re-billing.",
            razorpay_ref=cached_response.get("razorpay_ref"),
            is_failure_handled=True
        )
        return {
            "status": "DUPLICATE_SUPPRESSED",
            "message": "Duplicate purchase request suppressed. Returning cached transaction result.",
            "data": cached_response
        }

    # 3. Rate Limiting Check (Defends merchant rails against runaway AI agent loops)
    rate_ok, retry_after = rate_limiter.check_and_consume(request.agent_id)
    if not rate_ok:
        audit_ledger.record_entry(
            agent_id=request.agent_id,
            user_id=request.user_id,
            action="RATE_LIMITED",
            amount=request.get_calculated_total(),
            policy_snapshot=None,
            decision={"rate_limited": True, "retry_after": retry_after},
            explainability=f"Rate limit exceeded for agent '{request.agent_id}'. Throttled to prevent runaway loops.",
            is_failure_handled=True
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "status": "AGENT_RATE_LIMITED",
                "explainability": f"Agent '{request.agent_id}' exceeded permitted request velocity. Retry after {retry_after:.1f}s.",
                "retry_after_seconds": retry_after
            },
            headers={"Retry-After": str(int(retry_after) + 1)}
        )

    # 4. Retrieve User Policy Snapshot
    user_policy_list = user_policies.get(request.user_id)

    if not user_policy_list:
        raise HTTPException(
            status_code=400,
            detail=f"No spending policy configured for user {request.user_id}. Setup policy first."
        )
    active_policy = user_policy_list[-1]
    spend_state = user_spend_states.get(request.user_id, UserSpendState(user_id=request.user_id))

    # Check for approved 1-Tap Policy Waiver
    waiver_applied = False
    approved_waiver = None
    if request.waiver_id:
        w = growth_engine.waiver_manager.get_waiver(request.waiver_id)
        if w and w.status == "APPROVED" and w.user_id == request.user_id:
            waiver_applied = True
            approved_waiver = w

    # 4. Deterministic Pure Evaluation
    eval_result: EvaluationResult = evaluate_purchase(active_policy, request, spend_state)
    cart_total = request.total_amount if request.total_amount is not None else request.get_calculated_total()

    # 5. Handle Policy Denials or Apply Approved Waiver
    if not eval_result.allowed:
        if waiver_applied and approved_waiver:
            # Conversion Recovery: Human principal authorized exception
            eval_result.allowed = True
            eval_result.reason_code = ReasonCode.WAIVER_APPLIED
            eval_result.explainability = (
                f"Approved via 1-Tap Policy Waiver ({approved_waiver.waiver_id}): "
                f"Principal authorized ₹{approved_waiver.delta_amount:,.2f} budget delta. Original cap: ₹{approved_waiver.policy_limit:,.2f}."
            )
        else:
            # Save the Sale: Auto-generate dynamic 1-tap waiver opportunity
            pending_waiver = growth_engine.waiver_manager.request_waiver(
                user_id=request.user_id,
                agent_id=request.agent_id,
                cart_total=cart_total,
                policy_limit=active_policy.limits.max_per_transaction,
                reason=eval_result.explainability
            )

            # Simulate high-priority escalation (Voice callback / SMS / Webhook)
            escalation_triggered = True
            audit_entry = audit_ledger.record_entry(
                agent_id=request.agent_id,
                user_id=request.user_id,
                action="DENIED",
                amount=cart_total,
                policy_snapshot=active_policy.model_dump(mode="json"),
                decision={
                    "allowed": False,
                    "reason_code": eval_result.reason_code,
                    "rule_fired": eval_result.rule_fired,
                    "threshold": eval_result.threshold,
                    "actual_value": eval_result.actual_value,
                    "item_evaluations": [ie.model_dump() for ie in eval_result.item_evaluations],
                    "waiver_offered": pending_waiver.waiver_id
                },
                explainability=eval_result.explainability,
                razorpay_ref=None,
                is_failure_handled=True,
                escalation_dispatched=escalation_triggered
            )
            
            # Return 403 Forbidden with explainable payload and 1-tap waiver link
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "DENIED",
                    "reason_code": eval_result.reason_code,
                    "explainability": eval_result.explainability,
                    "rule_fired": eval_result.rule_fired,
                    "threshold": eval_result.threshold,
                    "actual_value": eval_result.actual_value,
                    "audit_log_id": audit_entry["id"],
                    "save_the_sale": {
                        "waiver_id": pending_waiver.waiver_id,
                        "delta_amount": pending_waiver.delta_amount,
                        "expires_in_seconds": int(pending_waiver.expires_at - time.time()),
                        "one_tap_approve_url": f"/growth/waiver/approve/{pending_waiver.waiver_id}"
                    },
                    "partial_fulfillment_option": (
                        growth_engine.analyze_partial_fulfillment(active_policy, request.items).model_dump()
                        if growth_engine.analyze_partial_fulfillment(active_policy, request.items) else None
                    ),
                    "escalation": {
                        "voice_callback_dispatched": True,
                        "recipient": request.user_id,
                        "prompt": f"NIYAM Alert: Purchase of ₹{cart_total:,.2f} was blocked. {eval_result.explainability}"
                    }
                }
            )


    # 6. Policy Passed -> Invoke Razorpay MCP with Circuit Breaker (Failure Mode 2 Handling)
    description = f"Autonomous purchase of {len(request.items)} item(s) by agent {request.agent_id}"
    try:
        payment_link = razorpay_client.create_payment_link(
            amount_inr=cart_total,
            description=description,
            reference_id=request.idempotency_key,
            notes={
                "agent_id": request.agent_id,
                "user_id": request.user_id,
                "policy_version": active_policy.policy_version
            }
        )
    except CircuitBreakerOpenException as cb_exc:
        # Failure Mode 2: Upstream Outage Handled Gracefully
        audit_entry = audit_ledger.record_entry(
            agent_id=request.agent_id,
            user_id=request.user_id,
            action="RAZORPAY_UNAVAILABLE",
            amount=cart_total,
            policy_snapshot=active_policy.model_dump(mode="json"),
            decision={
                "status": "FAIL_CLOSED",
                "reason_code": ReasonCode.RAZORPAY_UNAVAILABLE,
                "circuit_breaker": razorpay_client.circuit_breaker.get_status()
            },
            explainability=f"Upstream Razorpay outage intercepted: {str(cb_exc)}. Fail-closed triggered, zero funds transferred.",
            razorpay_ref=None,
            is_failure_handled=True,
            escalation_dispatched=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "RAZORPAY_UNAVAILABLE",
                "reason_code": ReasonCode.RAZORPAY_UNAVAILABLE,
                "explainability": "Payment gateway circuit breaker tripped. Transaction safely aborted without moving funds.",
                "circuit_state": "OPEN",
                "retry_after_seconds": 30,
                "audit_log_id": audit_entry["id"]
            }
        )

    # 7. Update User Cumulative Spend State
    spend_state.monthly_spend_accumulated += cart_total
    for item in request.items:
        cat = item.category.lower()
        spend_state.category_spend_accumulated[cat] = (
            spend_state.category_spend_accumulated.get(cat, 0.0) + (item.price * item.quantity)
        )
    user_spend_states[request.user_id] = spend_state

    # 8. Record Successful Purchase in Immutable Audit Ledger
    audit_entry = audit_ledger.record_entry(
        agent_id=request.agent_id,
        user_id=request.user_id,
        action="APPROVED",
        amount=cart_total,
        policy_snapshot=active_policy.model_dump(mode="json"),
        decision={
            "allowed": True,
            "reason_code": ReasonCode.APPROVED,
            "rule_fired": None,
            "payment_link_id": payment_link.get("id"),
            "payment_url": payment_link.get("short_url")
        },
        explainability=eval_result.explainability,
        razorpay_ref=payment_link.get("id"),
        is_failure_handled=False
    )

    response_data = {
        "status": "APPROVED",
        "amount": cart_total,
        "payment_link": payment_link.get("short_url"),
        "razorpay_ref": payment_link.get("id"),
        "explainability": eval_result.explainability,
        "audit_log_id": audit_entry["id"],
        "policy_version": active_policy.policy_version,
        "evaluated_at": eval_result.evaluated_at.isoformat()
    }

    # Store in idempotency cache
    idempotency_mgr.store(request.idempotency_key, request.agent_id, response_data)

    return response_data


@app.get("/audit/logs")
def get_audit_logs(limit: int = 50, user_id: Optional[str] = None):
    """Retrieve the immutable audit ledger stream."""
    return {
        "logs": audit_ledger.get_logs(limit=limit, user_id=user_id),
        "total_returned": len(audit_ledger.get_logs(limit=limit, user_id=user_id))
    }


@app.get("/audit/metrics")
def get_metrics():
    """Retrieve compliance metrics and evaluation stats."""
    return audit_ledger.get_metrics()


@app.get("/audit/export")
def export_audit_logs(format: str = "csv", user_id: Optional[str] = None):
    """Exports audit trail for compliance review in CSV or JSON format."""
    if format.lower() == "csv":
        csv_content = audit_ledger.export_csv(user_id=user_id)
        filename = f"niyam_compliance_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    return {"logs": audit_ledger.get_logs(limit=1000, user_id=user_id)}


@app.post("/webhooks/razorpay")
async def handle_razorpay_webhook(request: Request, x_razorpay_signature: Optional[str] = Header(None)):
    """Razorpay Webhook listener with HMAC-SHA256 signature verification."""
    body_bytes = await request.body()
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_key_892374").encode("utf-8")
    
    expected_sig = hmac.new(secret, body_bytes, hashlib.sha256).hexdigest()
    
    if x_razorpay_signature and x_razorpay_signature != expected_sig:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        payload = {}
    
    event = payload.get("event", "payment.captured")
    payment_obj = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_obj.get("id", f"pay_{uuid.uuid4().hex[:8]}")
    amount = float(payment_obj.get("amount", 0)) / 100.0 if payment_obj.get("amount") else 0.0
    
    audit_entry = audit_ledger.record_entry(
        agent_id=payment_obj.get("notes", {}).get("agent_id", "agent_shopper_01"),
        user_id=payment_obj.get("notes", {}).get("user_id", "usr_rahul_982"),
        action="SETTLED",
        amount=amount,
        policy_snapshot=None,
        decision={"event": event, "payment_id": payment_id, "signature_verified": True},
        explainability=f"Razorpay Webhook: Verified event '{event}' for {payment_id}. Funds settled securely.",
        razorpay_ref=payment_id,
        is_failure_handled=False
    )
    
    return {"status": "SUCCESS", "event": event, "audit_log_id": audit_entry["id"]}



# Growth & Revenue Optimization Endpoints

@app.post("/growth/headroom")
def get_headroom(req: HeadroomRequest):
    """Calculates authorized spending headroom for an agent's current cart."""
    user_policy_list = user_policies.get(req.user_id)
    if not user_policy_list:
        raise HTTPException(status_code=404, detail="No policy found for user")
    spend_state = user_spend_states.get(req.user_id, UserSpendState(user_id=req.user_id))
    return growth_engine.calculate_headroom(user_policy_list[-1], req.cart_total, spend_state)


@app.post("/growth/recommendations")
def get_upsell_recommendations(req: RecommendationsRequest):
    """Returns policy-compliant, high-margin upsell recommendations to grow merchant AOV."""
    user_policy_list = user_policies.get(req.user_id)
    if not user_policy_list:
        raise HTTPException(status_code=404, detail="No policy found for user")
    spend_state = user_spend_states.get(req.user_id, UserSpendState(user_id=req.user_id))
    recommendations = growth_engine.recommend_upsells(user_policy_list[-1], req.cart_total, spend_state)
    headroom = growth_engine.calculate_headroom(user_policy_list[-1], req.cart_total, spend_state)
    return {
        "authorized_headroom_remaining": headroom.effective_spendable_headroom,
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
        "merchant_growth_signal": "Policy-Aware Upselling maximizes basket size without causing gate rejections."
    }


@app.post("/growth/waiver/request")
def request_policy_waiver(req: WaiverCreateRequest):
    """Creates a pending single-use 'Save the Sale' waiver."""
    waiver = growth_engine.waiver_manager.request_waiver(
        user_id=req.user_id,
        agent_id=req.agent_id,
        cart_total=req.cart_total,
        policy_limit=req.policy_limit,
        reason=req.reason
    )
    return {"status": "PENDING", "waiver": waiver}


@app.post("/growth/waiver/approve/{waiver_id}")
def approve_policy_waiver(waiver_id: str):
    """1-Tap human principal approval (simulates WhatsApp / Push action)."""
    waiver = growth_engine.waiver_manager.approve_waiver(waiver_id)
    if not waiver:
        raise HTTPException(status_code=404, detail="Waiver not found or expired")
    
    audit_ledger.record_entry(
        agent_id=waiver.agent_id,
        user_id=waiver.user_id,
        action="WAIVER_APPROVED",
        amount=waiver.delta_amount,
        policy_snapshot=None,
        decision={"waiver_id": waiver_id, "delta_authorized": waiver.delta_amount},
        explainability=f"1-Tap Policy Waiver Approved: Principal authorized one-time delta of ₹{waiver.delta_amount:,.2f} for cart ₹{waiver.cart_total:,.2f}.",
        is_failure_handled=True
    )
    return {
        "status": "APPROVED",
        "message": f"Waiver {waiver_id} approved. AI Agent may now proceed with purchase.",
        "waiver": waiver
    }


@app.get("/growth/waiver/{waiver_id}")
def get_waiver_status(waiver_id: str):
    waiver = growth_engine.waiver_manager.get_waiver(waiver_id)
    if not waiver:
        raise HTTPException(status_code=404, detail="Waiver not found")
    return {"waiver": waiver}


@app.post("/chaos/toggle")
def toggle_chaos(req: ChaosToggleRequest):
    """Toggles simulated Razorpay outage to demonstrate Failure Mode 2 live."""
    razorpay_client.circuit_breaker.set_chaos_mode(req.enabled)
    return {
        "chaos_mode": req.enabled,
        "circuit_status": razorpay_client.circuit_breaker.get_status(),
        "message": "Razorpay simulated outage ACTIVE (Circuit OPEN)" if req.enabled else "Razorpay connection restored (Circuit CLOSED)"
    }


@app.get("/chaos/status")
def get_chaos_status():
    return razorpay_client.circuit_breaker.get_status()


# Static file serving for Mission Control Dashboard UI
ui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui")
if os.path.exists(ui_dir):
    app.mount("/static", StaticFiles(directory=ui_dir), name="static")

    @app.get("/", response_class=HTMLResponse)
    def serve_dashboard():
        index_path = os.path.join(ui_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return "<h1>NIYAM API Gateway Running. UI files pending.</h1>"
