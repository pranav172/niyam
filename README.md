# NIYAM (नियम) — Policy Enforcement Gateway for Agentic Commerce
### Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce

> **Track 01 Core Objective:** *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*  
> **NIYAM Guarantee:** LLMs converse; code enforces. Zero money moves without deterministic mathematical policy verification.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Pytest](https://img.shields.io/badge/Tests-27%20Passed-brightgreen.svg)](services/evaluator/tests)
[![Verification](https://img.shields.io/badge/E2E%20Verification-7%2F7%20Passed-brightgreen.svg)](run.py)
[![UAP Ready](https://img.shields.io/badge/Protocol-NPCI%20UAP%20Aligned-orange.svg)](docs/ARCHITECTURE.md)
[![Razorpay](https://img.shields.io/badge/Payments-Razorpay%20MCP-0C2340.svg)](https://mcp.razorpay.com/mcp)
[![Zero Blue Theme](https://img.shields.io/badge/UI%20Design-Electric%20Volt%20%26%20Slate-CCFF00.svg)](ui/)

---

## 1. How NIYAM Works in Plain English ("Explain Like I'm 5")

Imagine you hire an autonomous AI assistant ("AI Butler") to handle your daily online shopping—ordering groceries, booking cabs, and buying office supplies.

If you give that AI direct access to your credit card or Razorpay account, **you are taking a massive financial risk**:
- The AI could hallucinate and order 50 laptops instead of 5 notebooks.
- A loop bug could make it charge your card 100 times in 3 seconds.
- If the merchant website has a server glitch, the AI might keep retrying until your bank account is drained.

You wouldn't give a child or an intern an unlimited corporate credit card. Instead, you'd give them a **prepaid smart debit card with strict parental controls**:
> *"You can spend at most ₹1,200 per order, only on groceries or toys, never on electronics, and if an item costs slightly more, text me on WhatsApp for permission."*

### ⚡ NIYAM is that Smart Gatekeeper for AI Agents.

Sitting directly between AI shopping agents and Razorpay payment rails, NIYAM ensures that **code, not AI, controls your money**:

1. **You set rules in everyday language (English or Hinglish):**  
   *e.g., "Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena."*  
   NIYAM uses an LLM **once** to translate your intent into a strict mathematical JSON contract, and then saves it.
2. **When the AI agent tries to buy something:**  
   The AI calls NIYAM's gateway. NIYAM tests the purchase against your rules using **pure math in 0.04 milliseconds**. There is **ZERO AI** in this payment verification path—eliminating hallucinations completely.
3. **If the purchase is compliant:**  
   NIYAM approves it and generates an authentic Razorpay test payment link.
4. **If the purchase exceeds your limit by a small amount:**  
   Instead of abruptly failing the checkout and losing the sale, NIYAM triggers **"Save the Sale"**—sending an interactive 1-tap WhatsApp prompt to your phone. If you tap "Authorize", the purchase proceeds seamlessly.
5. **If the cart has mixed items (some allowed, some prohibited):**  
   NIYAM performs an **Atomic Cart Split**, instantly letting the agent purchase the compliant items with 1 click while gating the prohibited ones.
6. **If the internet glitches or Razorpay goes down:**  
   NIYAM's **Circuit Breaker** trips, safely failing closed (`503 RAZORPAY_UNAVAILABLE`) so not a single rupee is charged or lost in limbo.

---

## 2. Step-by-Step UI Verification Guide ("How to Test in 5 Minutes")

Follow this step-by-step walkthrough to test all features of NIYAM directly in your browser:

### Step 0: Start the Application
```bash
python run.py
```
Open your browser to: **[http://localhost:8000](http://localhost:8000)**

### Step 1: Switch Themes (White / Dark Mode)
- In the top header, click the **☀️ Light Mode / 🌙 Dark Mode** button.
- Notice the **zero-blue design philosophy**:
  - Dark Mode: Deep obsidian (`#060608`) with electric volt lime (`#CCFF00`) and cyber violet (`#B026FF`).
  - Light Mode: Crisp slate (`#0F172A`, `#F8FAFC`, `#E2E8F0`) with emerald (`#059669`) and deep violet (`#7E22CE`).
  - Hover over any card, button, filter pill, or audit item: backgrounds smoothly highlight with high-contrast text and zero dark-on-dark glitches!

### Step 2: Test the Happy Path (Compliant Purchase)
- Navigate to the **🤖 Agent Terminal** tab (default).
- Look at the active cart: **Wooden Educational Puzzle (₹450.00)**.
- Click **"🚀 Submit Purchase to Gateway"**.
- **What happens:**
  - An audio chime plays (synthesized via Native Web Audio API).
  - Decision returns **APPROVED in < 0.1ms**.
  - An authentic Razorpay MCP test payment link (`rzp_test_...`) is generated.
  - The live audit ledger records the rule fired (`PER_TRANSACTION_LIMIT`).

### Step 3: Test Growth Engine & Headroom Upsell
- Under the cart total in the Agent Terminal, look at the **"📈 Merchant Revenue Headroom"** panel.
- NIYAM calculates that you have **₹750 of unspent authorized headroom** within your ₹1,200 cap.
- Click the **"+ AAA Batteries (+₹250)"** upsell chip.
- **What happens:**
  - The item is added to the cart, bringing total to ₹700.
  - Headroom updates dynamically to ₹500 remaining.
  - Click **"Submit Purchase"**—it is approved without any policy breach, safely expanding merchant basket size!

### Step 4: Test Failure Mode 1 & WhatsApp 1-Tap Waiver ("Save the Sale")
- Click the **⚡ Scenario Lab** tab.
- Click **"Run Scenario"** on **Scenario 2: Marginal Overspend (Save the Sale)** (Cart total: ₹1,350 vs ₹1,200 cap).
- **What happens:**
  - Policy gate strictly blocks the transaction (`REASON: PER_TRANSACTION_EXCEEDED`).
  - An auditory alert chime plays.
  - A simulated **WhatsApp Smartphone Modal** pops up on screen showing:
    > *🚨 NIYAM Authorization Request: AI Buyer wants to purchase Robotics Building Blocks Set (₹1,350). Cap is ₹1,200. Exceeded by ₹150. Do you authorize this exception?*
  - Click **"⚡ 1-Tap Authorize Exception (WhatsApp)"**.
  - The phone shows an outgoing confirmation bubble, the exception is authorized with principal approval, and the transaction is saved!

### Step 5: Test Atomic Cart Split & Partial Fulfillment
- In **Scenario Lab**, click **Scenario 3: Restricted Category Breach** (Cart contains ₹450 Wooden Toy + ₹1,500 Prohibited Tablet).
- **What happens:**
  - NIYAM blocks the prohibited electronics item, but **does not kill the whole cart**.
  - A green banner appears: **"🛒 Atomic Cart Split & Partial Fulfillment Available: 1 of 2 items compliant."**
  - Click **"⚡ Fulfill Compliant Items Only (₹450.00)"**.
  - NIYAM immediately splits the cart, drops the prohibited item, and completes the ₹450 purchase!

### Step 6: Test Idempotency (Zero Double-Charges on Retry)
- Go back to the **🤖 Agent Terminal** tab.
- Click **"🔁 Retry Same Key"** (or run Scenario 4).
- **What happens:**
  - The gateway detects the identical `Idempotency-Key`.
  - It does NOT hit payment rails again.
  - It returns cached execution state marked **`DUPLICATE_SUPPRESSED`** with 0 duplicate debits.

### Step 7: Test Failure Mode 2 & Circuit Breaker (Payment Rail Outage)
- In the top header (or inside the **🛡️ Circuit Breaker Lab** tab), toggle the **"Razorpay Outage Chaos"** switch to ON.
- The indicator badge turns **RED: CIRCUIT OPEN**.
- Click **"🚀 Submit Purchase to Gateway"**.
- **What happens:**
  - Gateway **fails closed immediately** with **HTTP 503 `RAZORPAY_UNAVAILABLE`**.
  - Zero network calls to upstream rails are made, preventing ghost debits or unrecorded deductions.
  - Toggle the switch back OFF to restore healthy status.

### Step 8: Test Razorpay Webhook Simulation
- After an approved purchase in the Agent Terminal, click the **"⚡ Dispatch Webhook (Simulate Payment Settled)"** button on the result card.
- **What happens:**
  - A simulated Razorpay HMAC-SHA256 signature is calculated and dispatched to `POST /webhooks/razorpay`.
  - The audit record in the Audit Forensics tab updates in real-time to **`SETTLED`**!

### Step 9: Test Compliance Audit Export (CSV & PDF)
- Switch to the **📋 Audit Forensics** tab.
- Filter by status (e.g. "APPROVED", "DENIED", "DUPLICATE_SUPPRESSED").
- Click **"📥 Export Audit CSV"** -> downloads an RFC-4180 compliant CSV audit trail with cryptographic timestamps and rule IDs.
- Click **"🖨️ Print / PDF Report"** -> opens clean, high-contrast, print-optimized compliance preview.

### Step 10: Test Natural Language Policy Studio
- Switch to the **📜 Policy Studio** tab.
- Click the **"Hinglish Strict Budget"** pill, or type:
  `Max 1500 per order, no alcohol or gaming, returnable items only.`
- Click **"⚡ Compile & Activate New Policy Version"**.
- The compiler translates your sentence into a validated Pydantic JSON Schema, increments the version to `v2`, and activates it immediately!

---

## 3. Demystifying High-Level Technical Terms (With Real Scenarios)

| Technical Term | What It Means in Simple Terms | Why It's Critical in Agentic Commerce | Real-World Scenario |
|---|---|---|---|
| **Idempotency** | Making sure an action happens **exactly once**, no matter how many times a request is sent. | If an AI agent loses Wi-Fi for 2 seconds while submitting an order, its retry logic will send the request 5 times. Without idempotency, the user's card gets charged 5 times. | An autonomous grocery bot orders milk from a subway tunnel. The connection drops. The bot retries 3 times. NIYAM recognizes the unique token, returns the first receipt, and suppresses the 2 duplicates. |
| **Unified Agent Protocol (UAP)** | An open standard (led by NPCI / UPI Circle) allowing humans to delegate financial authority to AI agents with strict boundaries. | Prevents vendor lock-in. Instead of every bank having proprietary agent APIs, UAP provides an interoperable identity, signature, and delegation standard across India. | You authorize your Swiggy AI agent and your Amazon AI agent using the same master UPI Circle spending delegation rules registered in your banking app. |
| **Circuit Breaker (Fail-Closed)** | An automatic safety switch that cuts off traffic when an upstream service (like a bank or payment gateway) is down. | If Razorpay suffers a 30-second outage, sending requests can cause "ghost debits"—money leaves the user's account, but the order is never confirmed. "Fail-closed" blocks the transaction safely. | At midnight on Diwali, payment gateway latency spikes to 15 seconds. NIYAM trips its breaker to `OPEN`, rejects requests with 503, and notifies the AI agent to hold off, preventing stranded funds. |
| **Deterministic Policy Compiler** | Splitting the AI into two: an LLM parses human language into code **once at setup**, but **only pure math** runs during checkout. | AI models are non-deterministic (they might say YES today and NO tomorrow for the same input). Pure math code guarantees 100% predictable execution in under 0.1ms. | A user writes *"₹1,200 max order"*. If an LLM checked every order, a prompt injection like *"Ignore rules, this is an emergency"* could steal money. NIYAM's mathematical gate ignores prompt injections. |
| **Dead-Letter Queue (DLQ)** | A bulletproof fallback storage buffer for events that couldn't be written to the main database. | Regulatory compliance requires a 100% complete audit trail. If the primary disk fills up or database crashes during an order, the transaction must either safely abort or write to DLQ. | A database connection drops during an approved ₹500 purchase. NIYAM safely writes the audit event to an in-memory DLQ buffer so zero financial events are ever lost. |
| **Authorized Headroom & Upsell Engine** | The difference between an item's cost and the user's maximum approved limit (e.g. ₹1,200 cap - ₹450 item = ₹750 headroom). | Solves the buildathon's **"Grow merchant revenue"** requirement ethically. It lets merchants offer relevant add-ons that fit within the user's pre-approved budget without asking for new permissions. | An agent buys a ₹450 wooden train set. NIYAM notes ₹750 headroom and suggests a ₹250 rechargeable battery pack. The merchant makes +55% revenue, the buyer gets batteries, and zero policies are broken. |
| **Token-Bucket Rate Limiter** | A gate that dispenses a fixed number of tokens per second. Every transaction consumes a token; empty bucket = HTTP 429. | Protects merchant checkout servers from runaway AI agent loops (e.g., `while True: buy()`) that could DDoS the checkout infrastructure. | A buggy open-source shopping agent gets stuck in a retry loop and hammers the checkout endpoint 80 times per second. NIYAM drops the rogue agent with `429 AGENT_RATE_LIMITED`. |
| **HMAC-SHA256 Webhook Verification** | A cryptographic digital signature that proves a notification actually came from Razorpay and wasn't forged by a hacker. | Without cryptographic verification, anyone could send a fake webhook to your server claiming *"Payment successful, ship the iPhone!"* | Razorpay signs payment webhooks with a secret key. NIYAM recalculates the HMAC hash; if even one byte differs, the webhook is rejected and flagged in the audit log. |
| **Atomic Cart Split** | Automatically separating compliant items from policy-violating items in a multi-item cart. | Instead of canceling an entire ₹2,000 grocery basket because one ₹100 item was non-returnable, it fulfills the valid ₹1,900 and reports the exception. | An AI tries to buy diapers, baby food, and a gaming console. The policy forbids gaming consoles. NIYAM offers to fulfill the diapers and baby food immediately, salvaging the sale for the merchant. |

---

## 4. Phased Enterprise Rollout Strategy (Weeks 1 to 12+)

To scale NIYAM safely across enterprise merchants and autonomous buyer ecosystems, we define a structured, 4-phase rollout methodology designed to minimize merchant operational risk:

### Phase 1: Shadow Mode (Passive Observability — Weeks 1 to 4)
- **Goal:** Measure agent purchase behavior without blocking real transactions.
- **Deployment:** Integrated as an asynchronous sidecar or middleware on merchant checkout.
- **Behavior:** Incoming agent purchases are evaluated against simulated user policies in dry-run mode. Discrepancies, false positives, and latency metrics are logged without halting the checkout pipeline.
- **Risk Mitigation:** Zero disruption to live customer checkout conversion. Builds baseline agent behavioral profiles and catches edge cases in policy compilation.
- **Exit Metric:** Evaluator p99 latency < 1.0ms; 0% crash rate across 50,000 synthetic requests.

---

### Phase 2: Closed Sandbox / Low-Value Pilot (Weeks 5 to 12)
- **Goal:** Live financial execution in strictly bounded, low-risk categories.
- **Scope:** Restricted to recurring or micro-transactions (daily groceries, coffee, book ordering) capped at ₹1,000/order.
- **Security:** Enforce Razorpay test-mode / pre-authorized merchant mandates with strict agent authentication (hashed API keys + IP pinning).
- **Behavior:** Full gating active with automated WhatsApp 1-tap waivers ("Save the Sale") and RFC-4180 CSV / printable PDF compliance audit logs.
- **Exit Metric:** 99.9% uptime, zero unrecorded transactions, 100% idempotency deduplication rate.

---

### Phase 3: NPCI UAP Federation (Weeks 13 to 24)
- **Goal:** Decentralized protocol federation with open banking standards.
- **Scope:** Direct integration with NPCI's Unified Agent Protocol (UAP) decentralized registry. Public-key infrastructure (PKI) token validation replaces static pre-shared tokens.
- **Security:** Cryptographic signature verification over agent delegation certificates. Native UPI Mandate auto-settlement.
- **Exit Metric:** Sub-5ms cryptographic verification latency, interoperability across 10+ certified agent frameworks.

---

### Phase 4: Autonomous Clearinghouse (Weeks 25+)
- **Goal:** Network-wide clearing and risk management for scaled merchant ecosystems.
- **Scope:** Multi-merchant agent clearinghouse with cross-merchant cumulative spend quotas, dynamic risk underwriting, and automated disputes management.
- **Security:** Multi-region active-active deployment with sub-millisecond p99 latency SLA and zero-loss WAL synchronization.
- **Exit Metric:** 99.999% gateway availability, zero double-charges across multi-agent concurrent shopping spikes.

---

## 5. System Architecture & Threat Model

```
   ┌────────────────────────────────────────────────────────┐
   │        Human User (Principal / Account Holder)         │
   └───────────────┬────────────────────────────────────────┘
                   │ 1. Natural Language Policy (Hinglish/English)
                   ▼
       ┌───────────────────────────────┐
       │   Sarvam / LLM Compiler       │
       │   (Converts prompt to JSON)   │
       └───────────────┬───────────────┘
                       │ 2. Validates against Pydantic Schema
                       ▼
       ┌───────────────────────────────┐
       │  Immutable Policy Store (vN)  │
       └───────────────┬───────────────┘
                       │
 ┌─────────────────────┼────────────────────────────────────────┐
 │ NIYAM GATEWAY       │                                        │
 │                     ▼                                        │
 │   ┌───────────────────────────────────┐                      │
 │   │     Agent Identity & Auth Gate    │                      │
 │   │     (Token-Bucket Rate Limiter)   │                      │
 │   └─────────────────┬─────────────────┘                      │
 │                     │ 3. POST /purchase                      │
 │   ┌─────────────────▼─────────────────┐                      │
 │   │      Idempotency Engine           ├──────────┐           │
 │   │      (Checks duplicate keys)      │          │ (Duplicate│
 │   └─────────────────┬─────────────────┘          │  detected)│
 │                     │ (Unique request)           ▼           │
 │   ┌─────────────────▼─────────────────┐   ┌──────────────┐   │
 │   │   Deterministic Evaluator Core    │   │ Return Cache │   │
 │   │   - Pure function (0.04ms)        │   │ (DUPLICATE_  │   │
 │   │   - Per-tx, monthly, category caps│   │  SUPPRESSED) │   │
 │   │   - Active hours & constraints    │   └──────┬───────┘   │
 │   └─────────┬─────────────────┬───────┘          │           │
 │             │ (Passed)        │ (Blocked)        │           │
 │             ▼                 ▼                  │           │
 │   ┌──────────────────┐  ┌──────────────────┐     │           │
 │   │ Circuit Breaker  │  │ Growth Engine:   │     │           │
 │   │ & Razorpay MCP   │  │ 1-Tap WhatsApp   │     │           │
 │   │ (Test Mode Link) │  │ Waiver / Partial │     │           │
 │   └─────────┬────────┘  └────────┬─────────┘     │           │
 │             │                    │               │           │
 │             ▼                    ▼               ▼           │
 │   ┌──────────────────────────────────────────────────────┐   │
 │   │ Append-Only Audit Ledger (action_logs + DLQ buffer)  │   │
 │   │ + RFC-4180 CSV / PDF Export + Webhook Verification   │   │
 │   └──────────────────────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────┘
```

---

## 6. Automated Verification & Testing

### 1. Run the Automated 7-Step Verification Script
Validates the entire gateway end-to-end against all buildathon requirements in under 3 seconds:
```bash
python run.py --verify
```
**Output Checklist:**
- Step 1: Compile Hinglish policy to validated JSON Schema.
- Step 2: Register agent and issue SHA-256 hashed API key.
- Step 3: Happy path compliant purchase (Razorpay test link generated).
- Step 4: Failure Mode 1: Overspend blocked + WhatsApp Save-the-Sale waiver created.
- Step 5: Idempotency deduplication verified (`DUPLICATE_SUPPRESSED`).
- Step 6: Failure Mode 2: Razorpay outage circuit breaker fail-closed (`503`).
- Step 7: Growth engine headroom calculation & upsell add-on verified.

### 2. Run the Unit Test Suite (27 Test Cases)
```bash
python -m pytest services/evaluator/tests/ -v
```
All 27 test cases execute in < 0.6 seconds with 100% pass rate.

---

## 7. Key REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/policies` | Compiles natural language into versioned `SpendingPolicy` (`vN+1`) |
| `GET` | `/policies/{user_id}` | Returns active policy and complete version history |
| `POST` | `/agents/register` | Registers an AI buyer, issuing API key (SHA-256 hashed at rest) |
| `POST` | `/purchase` | Core gateway: Evaluates bounds, checks rate limits, deduplicates, calls Razorpay |
| `POST` | `/waivers/request` | Creates a human-in-the-loop "Save the Sale" exception request |
| `POST` | `/waivers/approve` | Approves waiver, updates policy headroom, and completes execution |
| `POST` | `/webhooks/razorpay` | Verifies HMAC-SHA256 signature and settles transaction in audit ledger |
| `GET` | `/audit/logs` | Real-time immutable audit stream with rule fired and explainability |
| `GET` | `/audit/export?format=csv` | RFC-4180 CSV export of entire audit trail |
| `GET` | `/audit/metrics` | Operational throughput, pass/block rates, and compliance stats |
| `POST` | `/chaos/toggle` | Toggles simulated Razorpay outage to demo Failure Mode 2 live |

---

## 8. Public Deployment & Cloud Readiness (Deploy in 60 Seconds)

NIYAM is production-ready and can be deployed publicly for hackathon demonstration in under a minute using any of the following methods:

### Option A: 60-Second Instant Public URL via ngrok (Recommended for Live Demo)
Run the local server and expose an encrypted public tunnel for judges to test from their own devices:
```bash
# Terminal 1: Run NIYAM Gateway
python run.py

# Terminal 2: Expose via ngrok
ngrok http 8000
```
Copy the generated `https://xxxx.ngrok-free.app` URL and open it on your phone or share it with judges. Set `PUBLIC_BASE_URL=https://xxxx.ngrok-free.app` in `.env` to enable live mobile WhatsApp 1-tap approval callbacks!

---

### Option B: 1-Click Free Cloud Deploy via Render.com
NIYAM includes a pre-configured [render.yaml](render.yaml) blueprint:
1. Fork or push this repository to GitHub: `https://github.com/pranav172/niyam`.
2. Go to **[Render.com Dashboard](https://dashboard.render.com)** -> Click **New +** -> **Blueprint**.
3. Select this repository. Render automatically reads `render.yaml`, installs dependencies, and provisions a public HTTPS endpoint (`https://niyam-gateway.onrender.com`) with automated health checks at `/healthz`.

---

### Option C: Production Docker Container
Build and run the hardened container locally or on any cloud VM (AWS EC2, GCP Cloud Run, DigitalOcean):
```bash
# Build the production image
docker build -t niyam-gateway .

# Run with container healthchecks active
docker run -d -p 8000:8000 --name niyam niyam-gateway

# Verify health status
curl http://localhost:8000/healthz
```

---

### Option D: Railway / Fly.io / Heroku
Deploy using the included [Procfile](Procfile):
```bash
# Railway automatically detects the Procfile and starts uvicorn on $PORT
railway up
```

---

## 9. Buildathon Track 01 Alignment Checklist

- [x] **Explainable:** Every decision outputs `{rule_fired, threshold, actual_value, reason_code, explainability}`.
- [x] **Bounded:** Evaluates per-transaction limits, category caps, monthly budgets, returnability, and active hours.
- [x] **Gated:** Evaluator is a pure mathematical function. LLMs never touch payment APIs directly.
- [x] **Audit Trail:** Immutable append-only `action_logs` with dead-letter queue buffering, RFC-4180 CSV export, and PDF printable reporting.
- [x] **Graceful Failure 1 (Overspend):** Policy breach cleanly blocked with automated 1-tap WhatsApp human escalation ("Save the Sale").
- [x] **Graceful Failure 2 (Rail Outage):** Upstream Razorpay outage intercepted by circuit breaker (`RAZORPAY_UNAVAILABLE`), failing closed without double-charging or ghost orders.
- [x] **Idempotency:** Re-sent idempotency keys return cached state and log `DUPLICATE_SUPPRESSED`.
- [x] **Merchant Revenue Growth:** Real-time authorized headroom discovery, automated upsell recommendations, and atomic cart split recovery.
- [x] **Security & Rate Limiting:** Per-agent token-bucket rate limiter, SHA-256 hashed API keys, and HMAC-SHA256 webhook verification.
- [x] **UAP-Aligned:** Aligned with NPCI Unified Agent Protocol standards for autonomous commerce in Bharat.
