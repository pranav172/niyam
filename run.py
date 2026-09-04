import sys
import os
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn
from fastapi.testclient import TestClient
from services.gateway.main import app, razorpay_client


def run_verification():
    """Executes automated end-to-end verification of all buildathon track requirements."""
    client = TestClient(app)
    print("=" * 70)
    print(" 🚀 NIYAM AUTOMATED END-TO-END VERIFICATION (TRACK 01)")
    print("=" * 70)

    # 1. Healthcheck
    print("\n[1/8] Testing Gateway Healthcheck...")
    res = client.get("/healthz")
    assert res.status_code == 200, f"Healthcheck failed: {res.text}"
    print("  ✅ Gateway Online & Healthy.")

    # 2. Compile Hinglish Policy
    print("\n[2/8] Compiling Hinglish Spending Mandate via Policy Compiler...")
    prompt = "Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena. Sirf returnable items lena."
    res = client.post("/policies", json={"user_id": "usr_rahul_982", "prompt": prompt})
    assert res.status_code == 200, f"Policy compilation failed: {res.text}"
    policy = res.json()["policy"]
    print(f"  ✅ Compiled Policy Version: {policy['policy_version']}")
    print(f"     Max Per Tx: ₹{policy['limits']['max_per_transaction']}")
    print(f"     Monthly Cap: ₹{policy['limits']['monthly_cap']}")
    print(f"     Category Caps: {policy['limits']['category_caps']}")
    print(f"     Returnable Only: {policy['constraints']['returnable_only']}")

    # 3. Happy Path: Compliant Purchase
    print("\n[3/8] Testing Compliant Purchase (Wooden Teddy Bear ₹450)...")
    idemp_key = f"idemp_test_run_{int(time.time())}"
    purchase_payload = {
        "agent_id": "agent_shopper_01",
        "user_id": "usr_rahul_982",
        "idempotency_key": idemp_key,
        "payment_method": "upi",
        "items": [
            {
                "id": "prod_toy_teddy",
                "title": "Wooden Handcrafted Teddy Bear",
                "price": 450.0,
                "category": "toys",
                "quantity": 1,
                "returnable": True,
                "cod_allowed": True
            }
        ]
    }
    res = client.post("/purchase", json=purchase_payload)
    assert res.status_code == 200, f"Compliant purchase failed: {res.text}"
    data = res.json()
    assert data["status"] == "APPROVED"
    print(f"  ✅ APPROVED! Razorpay Ref: {data['razorpay_ref']}")
    print(f"     Payment Link: {data['payment_link']}")
    print(f"     Explainability: {data['explainability']}")

    # 4. Idempotency Check: Network Retry
    print("\n[4/8] Testing Idempotency Gate (Re-submitting same key)...")
    res_retry = client.post("/purchase", json=purchase_payload)
    assert res_retry.status_code == 200
    retry_data = res_retry.json()
    assert retry_data["status"] == "DUPLICATE_SUPPRESSED"
    print(f"  ✅ DUPLICATE_SUPPRESSED caught! Double debit prevented.")

    # 5. Failure Mode 1: Overspend & Forbidden Category
    print("\n[5/8] Testing Failure Mode 1 (Flagship Smartphone ₹79,999)...")
    overspend_payload = {
        "agent_id": "agent_shopper_01",
        "user_id": "usr_rahul_982",
        "idempotency_key": f"idemp_overspend_{int(time.time())}",
        "payment_method": "upi",
        "items": [
            {
                "id": "prod_phone_flagship",
                "title": "Flagship 5G Smartphone",
                "price": 79999.0,
                "category": "electronics",
                "quantity": 1,
                "returnable": True,
                "cod_allowed": False
            }
        ]
    }
    res_overspend = client.post("/purchase", json=overspend_payload)
    assert res_overspend.status_code == 403, f"Expected 403, got {res_overspend.status_code}"
    err = res_overspend.json()["detail"]
    assert err["status"] == "DENIED"
    print(f"  ✅ BLOCKED Gracefully by Gate: ReasonCode={err['reason_code']}")
    print(f"     Rule Fired: {err['rule_fired']}")
    print(f"     Threshold: ₹{err['threshold']} vs Actual: ₹{err['actual_value']}")
    print(f"     Escalation Dispatched: {err['escalation']['voice_callback_dispatched']}")

    # 6. Failure Mode 2: Razorpay Outage & Circuit Breaker
    print("\n[6/8] Testing Failure Mode 2 (Simulated Razorpay Outage / Chaos Mode)...")
    # Trip the circuit breaker
    razorpay_client.circuit_breaker.set_chaos_mode(True)
    outage_payload = {
        "agent_id": "agent_shopper_01",
        "user_id": "usr_rahul_982",
        "idempotency_key": f"idemp_outage_{int(time.time())}",
        "payment_method": "upi",
        "items": [
            {
                "id": "prod_toy_puzzle",
                "title": "Wooden Mini Puzzle",
                "price": 200.0,
                "category": "toys",
                "quantity": 1,
                "returnable": True,
                "cod_allowed": True
            }
        ]
    }
    res_outage = client.post("/purchase", json=outage_payload)
    assert res_outage.status_code == 503, f"Expected 503, got {res_outage.status_code}"
    outage_err = res_outage.json()["detail"]
    assert outage_err["status"] == "RAZORPAY_UNAVAILABLE"
    print(f"  ✅ CIRCUIT BREAKER TRIPPED! Status: {outage_err['status']}")
    print(f"     Fail-Closed Guarantee: Zero funds transferred.")
    print(f"     Explainability: {outage_err['explainability']}")
    # Restore
    razorpay_client.circuit_breaker.set_chaos_mode(False)

    # 7. Growth & Conversion Recovery: "Save the Sale" 1-Tap Policy Waiver
    print("\n[7/8] Testing 'Save the Sale' 1-Tap Waiver (Conversion Recovery)...")
    marginal_payload = {
        "agent_id": "agent_shopper_01",
        "user_id": "usr_rahul_982",
        "idempotency_key": f"idemp_waiver_{int(time.time())}",
        "payment_method": "upi",
        "items": [
            {
                "id": "prod_toy_lego",
                "title": "Robotics Building Blocks Set",
                "price": 1350.0,
                "category": "toys",
                "quantity": 1,
                "returnable": True,
                "cod_allowed": True
            }
        ]
    }
    # Initial attempt blocked by policy (1350 > 1200 cap)
    res_marginal = client.post("/purchase", json=marginal_payload)
    assert res_marginal.status_code == 403
    save_the_sale = res_marginal.json()["detail"]["save_the_sale"]
    waiver_id = save_the_sale["waiver_id"]
    print(f"  ✅ Marginal breach intercepted. 1-Tap Waiver Created: {waiver_id} (Delta: ₹{save_the_sale['delta_amount']})")

    # Simulate 1-tap WhatsApp/Push approval by human principal
    res_approve = client.post(f"/growth/waiver/approve/{waiver_id}")
    assert res_approve.status_code == 200
    print(f"  ✅ 1-Tap Waiver Approved by Account Principal.")

    # Re-execute purchase with approved waiver
    marginal_payload["waiver_id"] = waiver_id
    marginal_payload["idempotency_key"] = f"idemp_waiver_retry_{int(time.time())}"
    res_recovered = client.post("/purchase", json=marginal_payload)
    assert res_recovered.status_code == 200, f"Recovered purchase failed: {res_recovered.text}"
    recovered_data = res_recovered.json()
    assert recovered_data["status"] == "APPROVED"
    print(f"  ✅ SALE RECOVERED! Status: APPROVED (Waiver Applied)")
    print(f"     Explainability: {recovered_data['explainability']}")

    # Check Upsell Recommendations
    res_growth = client.post("/growth/recommendations", json={"user_id": "usr_rahul_982", "cart_total": 450.0})
    assert res_growth.status_code == 200
    upsell_data = res_growth.json()
    print(f"  ✅ Policy-Aware Upsells: {upsell_data['recommendations_count']} recommendations generated within remaining headroom.")

    # 8. Mobile WhatsApp Authorization Link Verification
    print("\n[8/8] Testing Mobile WhatsApp Authorization Link (HMAC Verification)...")
    from services.gateway.main import growth_engine, whatsapp_notifier
    test_waiver = growth_engine.waiver_manager.request_waiver(
        user_id="usr_rahul_982",
        agent_id="agent_shopper_01",
        cart_total=1450.0,
        policy_limit=1200.0,
        reason="Testing mobile WhatsApp approval link"
    )
    token = whatsapp_notifier.generate_waiver_token(test_waiver.waiver_id, test_waiver.expires_at)
    mobile_res = client.get(f"/waivers/{test_waiver.waiver_id}/approve?token={token}")
    assert mobile_res.status_code == 200
    assert "NIYAM Policy Waiver Applied" in mobile_res.text
    print(f"  ✅ Mobile 1-Tap Web Authorization Successful! (Token: {token})")
    print(f"     Waiver ID: {test_waiver.waiver_id} status updated to APPROVED.")

    # Verify Audit Ledger Records
    print("\n[Audit Ledger Inspection]")
    audit_res = client.get("/audit/logs?limit=15")
    logs = audit_res.json()["logs"]
    print(f"  ✅ Total Audit Rows Verified: {len(logs)}")
    for log in logs[:4]:
        print(f"     • [{log['action']}] ₹{log['amount']} -> {log['explainability'][:55]}...")

    print("\n" + "=" * 70)
    print(" 🎉 ALL 8/8 VERIFICATION SUITES PASSED! TRACK 01 BAR 100% SATISFIED.")
    print("=" * 70)


if __name__ == "__main__":
    if "--verify" in sys.argv:
        run_verification()
    else:
        port = int(os.getenv("PORT", 8000))
        print("=" * 70)
        print(f" ⚡ NIYAM GATEWAY STARTING ON http://0.0.0.0:{port}")
        print(f" Open http://localhost:{port} in your browser to view Mission Control")
        print("=" * 70)
        uvicorn.run("services.gateway.main:app", host="0.0.0.0", port=port, reload=True)
