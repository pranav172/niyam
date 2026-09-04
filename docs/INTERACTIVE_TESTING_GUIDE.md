# NIYAM — Interactive Feature Testing & Evaluation Guide
### Razorpay AI Buildathon (Track 01: AI Growth & Agentic Commerce)

This interactive guide walks through **every feature built in NIYAM**, explaining:
1. What the feature does.
2. How to test it in the Mission Control Dashboard or via cURL / Python.
3. What happens under the hood (the architectural mechanism).
4. The exact audit and terminal signals judges look for.

---

## Quick Launch

1. Start the server:
   ```bash
   python run.py
   ```
2. Open **[http://localhost:8000](http://localhost:8000)** in your browser.
3. You will see the **Cyber Emerald & Obsidian Dark Mode Dashboard** with an **Interactive Testing Playbook** across the top bar.

---

## 🎯 Test 1: Natural Language Policy Compilation (Hinglish/English)

### What it does:
Translates vernacular spending mandates into an immutable, versioned JSON Schema object. **The LLM's job finishes here.** No LLM is ever called during financial transactions.

### How to test:
1. Click **1️⃣ Compile Policy** in the top Playbook bar.
2. In Column 1 (Policy Studio), see the pre-filled prompt:
   > *"Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena. Sirf returnable items lena."*
3. Modify any number (e.g. change 1200 to 1500) and click **⚡ Compile & Activate (vN+1)**.
4. **Observe:**
   - Active Policy badge updates from `v1` to `v2`.
   - JSON viewer displays the validated Pydantic schema: `limits.max_per_transaction: 1500`, `category_caps: {"electronics": 0}`, `returnable_only: true`.
   - An immutable `POLICY_CREATED` event appears in the Live Audit Ledger.

---

## 🎯 Test 2: Compliant Purchase (Happy Path Gate)

### What it does:
An AI agent attempts a purchase that complies with all policy bounds. Evaluates through the pure deterministic core, invokes Razorpay MCP in test mode, and generates an authentic payment link.

### How to test:
1. Click **2️⃣ Compliant Purchase (₹450)** in the top Playbook bar.
2. The cart automatically loads:
   - Item: *Wooden Handcrafted Teddy Bear*
   - Price: ₹450.00 (under ₹1,200 limit)
   - Category: `toys` (allowed)
   - Returnable: `true` (compliant)
3. Click **🚀 Submit Purchase to Gateway**.
4. **Observe:**
   - Green banner: **Transaction APPROVED by Deterministic Gate!**
   - Clickable link generated: `https://rzp.io/i/test_...` (can be paid with `success@razorpay`).
   - Audit Ledger records an `APPROVED` row with the exact policy snapshot and Razorpay reference.

---

## 🎯 Test 3: Growth Engine & Policy-Aware Upsells (+AOV)

### What it does:
Proves the Track 01 requirement: *"Grow the merchant's revenue, and make them sellable to AI buyers."* When an agent has unspent authorized headroom under its mandate, NIYAM suggests high-margin add-ons without violating category or budget caps.

### How to test:
1. Click **3️⃣ Growth Upsell (+₹250 AOV)** in the top Playbook bar.
2. Notice the **Authorized Headroom Box**:
   - `Authorized Headroom: ₹750.00 Available` (₹1,200 cap − ₹450 cart).
3. Click the button: **➕ Eco Rechargeable Battery Pack (+₹250)**.
4. **Observe:**
   - The battery pack is added to the cart payload.
   - Cart total increases from ₹450 to ₹700 (boosting merchant Average Order Value by 55%!).
   - Remaining headroom recalculates in real-time to ₹500.
   - Click **Submit Purchase** -> Still approved because it's within the ₹1,200 limit!

---

## 🎯 Test 4: Failure Mode 1 & "Save the Sale" 1-Tap Waiver

### What it does:
Demonstrates graceful failure handling and conversion recovery. An AI agent attempts an overspend purchase. NIYAM blocks unauthorized funds, alerts the human principal, and offers a **1-Tap WhatsApp/Push Waiver** to recover the conversion!

### How to test:
1. Click **4️⃣ Failure Mode 1 (Overspend & Waiver)** in the top Playbook bar.
2. The cart loads a *Robotics Kit* for ₹1,350 (₹150 over the ₹1,200 cap).
3. Click **🚀 Submit Purchase to Gateway**.
4. **Observe:**
   - Red denial banner: `BLOCKED: PER_TRANSACTION_LIMIT_EXCEEDED` (Delta: ₹150 over budget).
   - High-priority escalation banner fires: *Simulated Voice Callback / SMS alert dispatched*.
   - Blue Conversion Recovery card appears:
     > *"💡 Save the Sale Triggered: Order exceeds limit by ₹150.00. Principal can authorize this one-time purchase with 1-tap."*
5. Click **📲 1-Tap Authorize Exception via WhatsApp / Push**.
6. **Observe:**
   - The waiver is validated and attached to the purchase payload.
   - The transaction immediately succeeds: **Status: APPROVED (Waiver Applied)**!
   - The merchant converts a sale that would otherwise have been abandoned.

---

## 🎯 Test 5: Idempotency Retry Protection (Zero Double-Debits)

### What it does:
Autonomous agents retry on network timeouts. NIYAM guarantees at-most-once financial execution using `idempotency_key` deduplication.

### How to test:
1. Click **5️⃣ Idempotency (Retry Safe)** in the top Playbook bar.
2. Click **🚀 Submit Purchase to Gateway** -> Transaction approved.
3. Immediately click **🔁 Retry Same Key** (or submit again without changing the key).
4. **Observe:**
   - Purple badge: `DUPLICATE_SUPPRESSED`.
   - Message: *"Duplicate purchase request suppressed. Returning cached transaction result."*
   - No duplicate Razorpay payment link or charge is created.

---

## 🎯 Test 6: Failure Mode 2 & Circuit Breaker (Razorpay Outage)

### What it does:
Demonstrates our second distinct graceful failure mode. Upstream payment gateways occasionally suffer outages. NIYAM's circuit breaker fails closed with a `503`, preventing ghost debits or unrecorded purchases.

### How to test:
1. Click **6️⃣ Failure Mode 2 (Chaos Outage)** in the top Playbook bar.
2. Notice the **Razorpay Outage Chaos Switch** in the top right flips to `OUTAGE ACTIVE (OPEN)`.
3. Click **🚀 Submit Purchase to Gateway**.
4. **Observe:**
   - Yellow warning banner: `⚠️ CIRCUIT BREAKER FAIL-CLOSED: RAZORPAY_UNAVAILABLE`.
   - Reason: *"Upstream Razorpay outage intercepted. Fail-closed triggered, zero funds transferred."*
   - Audit Ledger logs an immutable record with state `FAIL_CLOSED`.

---

## 🧪 Automated Verification in Terminal

To run all scenarios automatically in 3 seconds:
```bash
python run.py --verify
```

To run all 21 unit tests:
```bash
python -m pytest -v
```
