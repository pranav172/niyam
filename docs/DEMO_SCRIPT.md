# NIYAM — 5-Minute Pitch & Demo Script
### Razorpay AI Buildathon — Track 01 (AI Growth & Agentic Commerce)

> **Timer:** Exactly 5 Minutes  
> **Target Audience:** Razorpay Judges & Technical Evaluators  
> **Key Thesis:** LLMs converse; code enforces. NIYAM makes agentic commerce explainable, bounded, and gated.

---

### [0:00 - 0:45] The Problem & The "Why Now"
- **Hook:** "Autonomous shopping agents are already browsing the web and comparing products. But here's the billion-dollar question: *Would you give an autonomous LLM your credit card or UPI credentials?*"
- **The Gap:** "LLMs hallucinate, suffer prompt injections, and lack deterministic boundaries. If an agent loops or misinterprets instructions, an account can be wiped out in seconds."
- **Why Now:** "NPCI is rolling out the Unified Agent Protocol (UAP) extending UPI Circle delegations to software agents. But merchants and buyers need an enforcement gateway **today** that guarantees no money moves without mathematical, deterministic policy approval."

---

### [0:45 - 1:30] Solution & Natural Language Policy Compilation
- **Show UI:** Open NIYAM Mission Control Dashboard (`http://localhost:8000`).
- **Demo Action:** Enter conversational Hinglish policy in the Policy Studio:
  > *"Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, aur monthly 8000 se upar mat hone dena."*
- **Click 'Compile Policy':**
  - Point to the generated JSON: Notice `policy_version: v1`, `max_per_transaction: 1200`, `category_caps: {"electronics": 0, "toys": 1500}`.
  - Explain: "The LLM's job ends right here at compile-time. At purchase time, no LLM is in the money path."

---

### [1:30 - 2:15] Demo Failure Mode 1: Overspend / Policy Breach
- **Demo Action:** Under 'Autonomous Agent Shopper', select Scenario: **"Breach Attempt (Flagship Smartphone ₹79,999)"**.
- **Click 'Execute Purchase':**
  - Request immediately **DENIED**.
  - Highlight the Live Audit Ledger row:
    - `Decision: DENIED`
    - `Rule Fired: limits.max_per_transaction`
    - `Threshold: ₹1,200 | Actual: ₹79,999`
    - `Explainability: Blocked: Cart amount ₹79,999 exceeds max limit ₹1,200 (Delta: ₹78,799 over).`
  - Highlight the Escalation Banner: "Automated Voice Callback / SMS alert dispatched to account principal."

---

### [2:15 - 2:45] Demo Failure Mode 2: Upstream Outage & Circuit Breaker
- **The Twist:** "The buildathon asks to show one failure handled gracefully. We show **two**."
- **Demo Action:** Flip the **"Razorpay Chaos Toggle"** to **OFFLINE / OUTAGE**.
- **Demo Action:** Attempt a valid purchase: **"Handcrafted Wooden Toy (₹450)"**.
- **Result:**
  - Evaluator passes the policy check, but the Circuit Breaker catches the simulated Razorpay outage.
  - Returns `503 Service Unavailable` with `reason_code: RAZORPAY_UNAVAILABLE`.
  - Highlight the Audit Ledger: "Notice the decision: `FAIL_CLOSED`. No ghost order, no double debit, zero silent drops."

---

### [2:45 - 3:45] Happy Path: Compliant Purchase & Idempotent Retries
- **Demo Action:** Flip Chaos Toggle back to **NORMAL**.
- **Click 'Execute Purchase' for Wooden Toy (₹450):**
  - Result: **APPROVED!**
  - Payment Link generated: `https://rzp.io/i/test_...` (or test order).
  - Can be paid live in test mode with `success@razorpay`.
- **Demo Action (Idempotency):** Immediately click **"Retry with Same Idempotency Key"**.
  - Result: Returns cached receipt with `DUPLICATE_SUPPRESSED`.
  - Explain: "Network retries from AI agents will never double-charge your card."

---

### [3:45 - 5:00] Architecture, Performance & Conclusion
- **Show Audit Schema & Specs:** Point to the structured schema, sub-millisecond evaluation p99 latency (< 0.5ms), and the immutable dead-letter queue WAL.
- **Summary:**
  - **Bounded & Gated:** Pure deterministic evaluator.
  - **Explainable:** Every action has an itemized reason code and plain English/Hindi explanation.
  - **Resilient:** Two distinct failure modes handled cleanly.
- **Closing Punchline:** "NIYAM is the governance layer that unlocks agentic commerce for Bharat. Safe, auditable, and ready for UAP."
