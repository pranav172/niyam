# NIYAM (नियम) — Policy Enforcement Gateway for Agentic Commerce
### Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce

> **Track 01 Objective:** *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*  
> **NIYAM Guarantee:** LLMs converse; code enforces. Zero money moves without deterministic policy verification.

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Pytest](https://img.shields.io/badge/Tests-18%20Passed-brightgreen.svg)](services/evaluator/tests)
[![UAP Ready](https://img.shields.io/badge/Protocol-UAP%20Aligned-orange.svg)](docs/ARCHITECTURE.md)
[![Razorpay](https://img.shields.io/badge/Payments-Razorpay%20MCP-0C2340.svg)](https://mcp.razorpay.com/mcp)

---

## 1. What is NIYAM?

As autonomous AI agents evolve from conversational assistants into purchasing actors, commerce platforms face a critical trust barrier: **Non-deterministic AI models cannot be trusted with direct financial authorization.**

**NIYAM** is an enforcement gateway aligned with NPCI's upcoming **Unified Agent Protocol (UAP)** (which extends UPI Circle delegation models). NIYAM sits directly between autonomous AI shopping agents and Razorpay rails, providing:

1. **Deterministic Spending Control:** Natural language spending mandates (in English, Hindi, or Hinglish) are compiled into versioned JSON Schemas once at onboarding. At transaction time, evaluation is **100% pure mathematical code**—zero network calls, zero LLMs on the financial path, sub-millisecond p99 latency.
2. **Explainable Audit Ledger:** Every single decision is recorded in an immutable, append-only log (`action_logs`) capturing the exact rule fired, thresholds, and plain-language explanations.
3. **Two Distinct Failure Modes Handled Gracefully (Exceeding the 1-failure requirement):**
   - **Failure Mode 1 (Policy Breach):** High-spend or prohibited category attempts are blocked and routed to an automated human escalation/voice callback workflow.
   - **Failure Mode 2 (Upstream Outage):** A built-in circuit breaker intercepts Razorpay outages (`RAZORPAY_UNAVAILABLE`) and fails closed gracefully, preventing ghost debits or unrecorded orders.
4. **Idempotency by Design:** Prevents double-charging on autonomous agent retries (`DUPLICATE_SUPPRESSED`).
5. **Dead-Letter Queue (DLQ) Resilience:** Guarantees zero financial events execute without an audit log write, even during storage faults.

---

## 2. Architecture Overview

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

## 3. Quickstart

### Prerequisites
- Python 3.10+
- Dependencies: `pip install -r requirements.txt`

### 1. Run the Gateway & Mission Control UI
```bash
python run.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 2. Run the Automated 6-Step Verification Script
To verify the entire system end-to-end against the buildathon rubric in 3 seconds:
```bash
python run.py --verify
```

### 3. Run the Unit Test Suite (18 Test Cases)
```bash
python -m pytest services/evaluator/tests/ -v
```

---

## 4. Key Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/policies` | Compiles natural language into versioned `SpendingPolicy` (`vN+1`) |
| `GET` | `/policies/{user_id}` | Returns active policy and complete version history |
| `POST` | `/agents/register` | Registers an AI buyer, issuing API key (SHA-256 hashed at rest) |
| `POST` | `/purchase` | Core enforcement gateway: Evaluates bounds, deduplicates, calls Razorpay |
| `GET` | `/catalog/agent` | Agent-readable catalog with machine policy tags (returnable, COD, caps) |
| `GET` | `/audit/logs` | Real-time immutable audit stream with full decision metadata |
| `GET` | `/audit/metrics` | Operational throughput, pass/block rates, and compliance stats |
| `POST` | `/chaos/toggle` | Toggles simulated Razorpay outage to demo Failure Mode 2 live |

---

## 5. Documentation

- 📖 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Comprehensive architectural blueprint, threat model, security, and UAP alignment.
- 📐 **[docs/POLICY_SCHEMA.md](docs/POLICY_SCHEMA.md)**: JSON Schema specification and compiled examples.
- 🛡️ **[docs/FAILURE_MODES.md](docs/FAILURE_MODES.md)**: Reason code matrix and deep-dive into both graceful failure handling workflows.
- ⏱️ **[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)**: 5-minute timed presentation script for judges.

---

## 6. Buildathon Track 01 Checklist

- [x] **Explainable:** Every decision outputs `{rule_fired, threshold, actual_value, reason_code, explainability}`.
- [x] **Bounded:** Evaluates per-transaction limits, category caps, monthly budgets, returnability, and active hours.
- [x] **Gated:** Evaluator is a pure mathematical function. LLMs never touch payment APIs directly.
- [x] **Audit Trail:** Immutable append-only `action_logs` with dead-letter queue buffering.
- [x] **Graceful Failure 1:** Policy/overspend breach cleanly blocked with automated voice callback escalation.
- [x] **Graceful Failure 2:** Upstream Razorpay outage intercepted by circuit breaker (`RAZORPAY_UNAVAILABLE`), failing closed without double-charging or ghost orders.
- [x] **Idempotency:** Re-sent idempotency keys return cached state and log `DUPLICATE_SUPPRESSED`.
- [x] **UAP-Aligned:** Aligned with NPCI Unified Agent Protocol standards for autonomous commerce in Bharat.
