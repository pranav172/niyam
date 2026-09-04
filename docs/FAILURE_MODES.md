# NIYAM Failure Modes & Resilience Matrix

> **Track 01 Requirement:** *"Show the audit trail and one failure handled gracefully."*  
> **NIYAM Standard:** NIYAM demonstrates **two distinct failure modes** handled with zero data loss, zero silent drops, and full audit transparency.

---

## 1. Failure Modes Summary Table

| Reason Code | Trigger Condition | Evaluation Layer | Gateway Action | Audit Ledger State | User Notification / Escalation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`PER_TRANSACTION_LIMIT_EXCEEDED`** | Cart amount > `max_per_transaction` | Evaluator (Pure) | Hard Deny (403) | `DENIED` with threshold & delta | Voice / Push alert to principal |
| **`MONTHLY_CAP_EXCEEDED`** | Prior spend + cart > `monthly_cap` | Evaluator (Pure) | Hard Deny (403) | `DENIED` with cumulative spend | WhatsApp / SMS budget alert |
| **`CATEGORY_FORBIDDEN`** | Item category cap == 0 or forbidden | Evaluator (Pure) | Hard Deny (403) | `DENIED` with item ID & category | Policy violation badge in UI |
| **`CATEGORY_CAP_EXCEEDED`** | Item spend in category > category cap | Evaluator (Pure) | Hard Deny (403) | `DENIED` with category cap | Suggest alternative items |
| **`TIME_WINDOW_CLOSED`** | Request time outside active hours | Evaluator (Pure) | Hard Deny (403) | `DENIED` with active hours window | Re-queue request for next window |
| **`NON_RETURNABLE_ITEM`** | `returnable_only=true` & item non-returnable | Evaluator (Pure) | Hard Deny (403) | `DENIED` with product return policy | Agent prompts user for waiver |
| **`DUPLICATE_SUPPRESSED`** | Re-sent `idempotency_key` | Gateway Idempotency | Cache Replay (200) | `DUPLICATE_SUPPRESSED` | None (Transparent retry handling) |
| **`RAZORPAY_UNAVAILABLE`** | Razorpay MCP circuit breaker tripped / 5xx / timeout | MCP Client Circuit Breaker | Fail-Closed Deny (503) | `CIRCUIT_BREAKER_OPEN` | Merchant incident alert & retry queue |
| **`SCHEMA_VALIDATION_ERROR`** | Compiler output violates policy schema | Policy Compiler | Re-prompt / Reject | `COMPILATION_FAILED` with errors | Request clarification from user |

---

## 2. Deep Dive: Failure Mode 1 — Autonomous Overspend & Policy Breach

### Scenario Walkthrough
1. **Context:** User Rahul sets a policy: *"Max ₹1,200 per order, no electronics"*.
2. **Event:** Autonomous shopping agent finds a deal on a ₹79,999 flagship smartphone and attempts purchase:
   ```json
   POST /purchase
   {
     "agent_id": "shopping_bot_42",
     "items": [{"id": "prod_phone", "name": "Flagship 5G", "price": 79999, "category": "electronics"}]
   }
   ```
3. **Graceful Handling:**
   - Evaluator halts before contacting any payment rail.
   - Evaluator generates deterministic response:
     ```json
     {
       "allowed": false,
       "reason_code": "PER_TRANSACTION_LIMIT_EXCEEDED",
       "rule_fired": "limits.max_per_transaction",
       "threshold": 1200,
       "actual_value": 79999,
       "explainability": "Blocked: Total cart amount ₹79,999 exceeds maximum per-transaction limit of ₹1,200 (Delta: ₹78,799 over budget)."
     }
     ```
   - **User Escalation:** Dispatches an immediate high-priority escalation hook (`simulated_voice_callback` / SMS) with deep-link: *"Your AI Agent attempted a ₹79,999 electronics purchase. This violates your ₹1,200 cap. Tap to approve manual override."*
   - **Audit Record:** Immutable entry written to `action_logs` with snapshot of active `v1` policy.

---

## 3. Deep Dive: Failure Mode 2 — Upstream Razorpay Outage / Chaos Injection

### Scenario Walkthrough
1. **Context:** A valid purchase (e.g. ₹450 Wooden Toy) passes all policy checks.
2. **Event:** Upstream Razorpay MCP server experiences high latency, connection drops, or returns 503 HTTP status. (In demo mode, triggered via the **Chaos Switch**).
3. **Graceful Handling:**
   - The **Circuit Breaker** catches consecutive connection errors or high error rates.
   - **Fail-Closed Guarantee:** The circuit breaker trips into `OPEN` state.
   - Gateway returns `503 Service Unavailable`:
     ```json
     {
       "success": false,
       "status": "DENIED",
       "reason_code": "RAZORPAY_UNAVAILABLE",
       "explainability": "Payment gateway circuit breaker tripped. Transaction safely aborted without moving funds.",
       "retry_after_seconds": 30
     }
     ```
   - **No Ghost Debits:** The transaction is NOT marked completed, and no unbacked receipt is generated.
   - **Audit Row:** Written with `action: CIRCUIT_BREAKER_TRIPPED`, `decision: { "status": "FAIL_CLOSED" }`.

---

## 4. Resilience Architecture: Dead-Letter Queue (DLQ) for Audit Writes

In enterprise payments, **the audit write is as critical as the money movement**. If an audit write to the primary database fails after a successful payment link creation:
- NIYAM catches the DB exception.
- Immediately appends the exact JSON payload to a local append-only WAL (`dead_letter_queue.jsonl`).
- Background worker replays queued records once DB connection is restored.
- **Zero transactions execute without a permanent, verifiable audit trail.**
