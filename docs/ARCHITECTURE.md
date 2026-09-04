# NIYAM — Architecture & Design Document
### AI Growth & Agentic Commerce — Razorpay AI Buildathon (Track 01)

> **Track 01 Bar:** *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*  
> **NIYAM Guarantee:** Zero money moves without a deterministic policy check. LLMs converse; code enforces. Every decision produces an explainable, auditable record.

---

## 1. Executive Summary & Vision

As autonomous AI agents evolve from conversational assistants into purchasing actors, commerce platforms face a fundamental security and governance dilemma: **Non-deterministic AI models cannot be trusted with autonomous financial authorization.**

**NIYAM** (Sanskrit/Hindi for *Rule / Governance*) is a **Unified Agent Protocol (UAP)**-aligned policy enforcement gateway. Sitting directly between upstream AI shopping agents (buyers) and Razorpay payment rails (merchants), NIYAM guarantees:
1. **Deterministic Spending Control:** LLMs translate user intent into structured, versioned policies. However, at purchase time, evaluation is **100% pure, deterministic, and stateless**—no network calls, no LLM hallucinations, zero randomness.
2. **Comprehensive Audit Ledger:** Every single action attempt—whether approved, blocked, duplicate, or intercepted by a circuit breaker—is recorded in an append-only ledger with the exact rule fired, thresholds, and human-readable explanation.
3. **Dual Graceful Failure Modes:**
   - *Failure Mode 1 (Policy Violation):* High-spend or prohibited category attempts are blocked and routed to an automated human escalation/voice callback workflow.
   - *Failure Mode 2 (Upstream Outage):* A built-in circuit breaker intercepts Razorpay outages (`RAZORPAY_UNAVAILABLE`) and fails closed gracefully, preventing ghost charges or silent drops.
4. **Idempotency by Design:** AI agents retrying network requests cannot cause duplicate debits or ghost orders (`DUPLICATE_SUPPRESSED`).

---

## 2. Industry Alignment: NPCI Unified Agent Protocol (UAP)

### The Ecosystem Context
The National Payments Corporation of India (NPCI) is developing the **Unified Agent Protocol (UAP)** to extend India's UPI delegation framework (notably UPI Circle and UPI Mandates) to autonomous software agents. 

- **Not "Universal":** The official NPCI moniker is **Unified Agent Protocol (UAP)**.
- **Delegation Model:** UAP allows a human principal (e.g. account holder) to delegate pre-authorized spending mandates to authorized autonomous agents with bounded parameters (validity, maximum transaction amount, category limitations, merchant white-lists).
- **NIYAM's Positioning:** NIYAM does not require UAP to be fully live today; rather, **NIYAM is architected as UAP-compatible by design**. When NPCI rolls out agent registration registries, NIYAM seamlessly integrates upstream agent identity certificates while providing the required local merchant-side or buyer-side enforcement gateway.

---

## 3. High-Level Gateway Architecture

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
                       │ 2. Validates against JSON Schema
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
 │   └─────────────────┬─────────────────┘                      │
 │                     │ 3. POST /purchase                      │
 │   ┌─────────────────▼─────────────────┐                      │
 │   │      Idempotency Engine           ├──────────┐           │
 │   │      (Checks duplicate keys)      │          │ (Duplicate│
 │   └─────────────────┬─────────────────┘          │  detected)│
 │                     │ (Unique request)           ▼           │
 │   ┌─────────────────▼─────────────────┐   ┌──────────────┐   │
 │   │   Deterministic Evaluator Core    │   │ Return Cache │   │
 │   │   - Pure function                 │   │ (DUPLICATE_  │   │
 │   │   - Per-tx, monthly, category caps│   │  SUPPRESSED) │   │
 │   │   - Active hours & constraints    │   └──────┬───────┘   │
 │   └─────────┬─────────────────┬───────┘          │           │
 │             │ (Passed)        │ (Blocked)        │           │
 │             ▼                 ▼                  │           │
 │   ┌──────────────────┐  ┌──────────────────┐     │           │
 │   │ Circuit Breaker  │  │ Failure Handler  │     │           │
 │   │ & Razorpay MCP   │  │ (Voice Callback /│     │           │
 │   │ (Test Mode Link) │  │  User Alert)     │     │           │
 │   └─────────┬────────┘  └────────┬─────────┘     │           │
 │             │                    │               │           │
 │             ▼                    ▼               ▼           │
 │   ┌──────────────────────────────────────────────────────┐   │
 │   │ Append-Only Audit Ledger (action_logs + DLQ buffer)  │   │
 │   └──────────────────────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────┘
```

---

## 4. End-to-End Request Lifecycle

1. **Policy Onboarding:**
   The user inputs an operational mandate in conversational Hinglish or English:
   > *"Baccho ke toys ke liye max ₹1200 per order, electronics bilkul nahi, aur monthly ₹8000 se upar mat hone dena."*
2. **Deterministic Compilation:**
   The policy compiler uses Sarvam AI / structured LLM prompting to translate this string into a canonical, versioned JSON object (`v1`). If the output fails strict JSON Schema validation, it is rejected before any money path is exposed.
3. **Agent Registration:**
   The autonomous shopping agent registers with NIYAM, obtaining an `agent_id` authenticated via hashed API keys.
4. **Purchase Initiation (`POST /purchase`):**
   The agent submits a purchase payload containing `agent_id`, `items[]`, `total_amount`, and an `idempotency_key`.
5. **Idempotency Gate:**
   If the `idempotency_key` has already been processed within the TTL window, the gateway immediately returns the cached transaction state and logs a `DUPLICATE_SUPPRESSED` record.
6. **Pure Deterministic Evaluation:**
   The engine executes a pure function over the request, the user's cumulative spend state, and the active policy snapshot.
7. **Execution or Graceful Interception:**
   - **Case A (Approved):** The gateway invokes the Razorpay MCP Client (`create_payment_link` or `create_order`) in **Test Mode**. If Razorpay is experiencing an outage, the circuit breaker trips and returns `RAZORPAY_UNAVAILABLE`.
   - **Case B (Denied):** The transaction is halted immediately. A notification payload is dispatched to the user's phone / dashboard (simulating voice callback/SMS escalation).
8. **Audit Logging & Resilient Buffering:**
   An immutable record is written to `action_logs`. If the primary database is momentarily unreachable, the record is immediately committed to a local, durable Dead-Letter Queue (`dead_letter_queue.jsonl`) to guarantee zero unrecorded financial events.

---

## 5. Security & Boundary Architecture

- **No LLM on the Financial Path:** No LLM is ever called during `POST /purchase`. Evaluation latency is sub-millisecond, deterministic, and mathematically verifiable.
- **Test Mode Enforcement:** Razorpay API calls strictly enforce `rzp_test_...` key prefixes or sandbox execution.
- **Fail-Closed Guarantee:** Any unhandled exception, syntax error, or connection timeout defaults to `DENY`. Money never moves by default.
- **Key Hashing at Rest:** Agent API tokens are stored using SHA-256 digests. Raw keys are never logged or exposed in audit explainability payloads.
- **HMAC Webhook Verification:** Razorpay payment capture webhooks require cryptographic signature verification before updating transaction fulfillment state.

---

## 6. Scalability & Operational Design

- **Stateless Evaluator:** The core evaluator has zero external state and can horizontally scale to 100,000+ requests/sec across any container cluster.
- **Database Partitioning Strategy:** In production, high-frequency append-only audit logs are partitioned by month and separated from semantic product catalog vector storage.
- **Rate-Limiting per `agent_id`:** In addition to global IP rate limiting, token-bucket limits are enforced per agent ID to prevent runaway agent loops from exhausting merchant inventory or evaluation capacity.

---

## 7. Phased Rollout Roadmap

To scale NIYAM safely across enterprise merchants and autonomous buyer ecosystems, we define a structured, 4-phase rollout methodology designed to minimize merchant operational risk while validating zero-hallucination agentic commerce:

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

