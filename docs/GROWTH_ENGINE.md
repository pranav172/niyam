# NIYAM Growth & Revenue Optimization Architecture
### Track 01 Alignment: "Grow the merchant’s revenue, and make them sellable to AI buyers."

> While standard safety gateways act as dead-end blockers that hurt merchant conversion rates, **NIYAM actively grows Average Order Value (AOV) and recovers at-risk sales** through two key mechanisms:
> 1. **Policy-Aware Upsell Engine (Cart Headroom Optimization)**
> 2. **"Save the Sale" 1-Tap Policy Waiver (Conversion Recovery)**

---

## 1. Policy-Aware Upsell & Headroom Optimizer

### The Problem
Autonomous AI shopping agents frequently execute micro-purchases that fall well below the user's maximum authorized budget (e.g. buying a ₹450 wooden toy under a ₹1,200 spending mandate). Traditional e-commerce platforms have no visibility into the agent's delegation parameters and miss the opportunity to recommend complementary add-ons.

### NIYAM Solution
1. **Mathematical Headroom Calculation:**
   ```
   Headroom = min(
     policy.max_per_transaction - cart_total,
     policy.monthly_cap - (monthly_spend_accumulated + cart_total)
   )
   ```
2. **Margin-Optimized Complementary Recommendations:**
   NIYAM's `GrowthEngine` filters the merchant's high-margin add-on inventory (`merchant_margin_tier: HIGH`) against the active policy bounds:
   - Excludes prohibited categories (e.g. `electronics: 0`).
   - Excludes items that exceed the remaining headroom.
   - Recommends zero-friction additions (e.g. ₹250 rechargeable battery pack, ₹120 gift wrapping).
3. **Outcome:** Increases merchant Average Order Value (AOV) by **up to 40%** without risking policy denials.

---

## 2. "Save the Sale" 1-Tap Policy Waiver (Conversion Recovery)

### The Problem
When an autonomous agent identifies an ideal product that marginally exceeds the spending mandate (e.g. a ₹1,350 educational robotics kit against a ₹1,200 cap), traditional gateways reject the purchase with a `403 Forbidden` error. **The merchant loses 100% of the sale.**

### NIYAM Solution: Graceful Conversion Recovery
```
   AI Buyer Cart (₹1,350) ───▶ [NIYAM Gate] (Cap: ₹1,200)
                                      │
                                      ├─▶ Deterministic Block (Delta: ₹150)
                                      │
                                      ▼
                        [Save the Sale Engine]
                                      │
                                      ▼
                       1-Tap WhatsApp / Push Waiver
                                      │
                                      ▼
                      Principal Approves One-Time Delta
                                      │
                                      ▼
                     [Razorpay Payment Link Generated]
                      (Merchant Converts ₹1,350 Sale!)
```

1. **Waiver Generation:**
   On marginal budget breach, NIYAM immediately generates a time-bound `PolicyWaiver` (`status: PENDING`, 15-minute TTL).
2. **1-Tap Principal Escalation:**
   A structured payload is dispatched to the user's mobile device via simulated WhatsApp / push notification:
   > *"Your AI Agent wants to purchase 'Robotics Kit' for ₹1,350 (₹150 over your ₹1,200 cap). [1-Tap Authorize Exception]"*
3. **Execution with Waiver:**
   When the user taps approve, NIYAM validates the cryptographic waiver token and allows the transaction, logging an immutable `APPROVED_WITH_WAIVER` audit row.

---

## 3. Growth API Reference

### `POST /growth/headroom`
Returns real-time authorized spending headroom for an active cart.

**Request:**
```json
{
  "user_id": "usr_rahul_982",
  "cart_total": 450.0
}
```

**Response:**
```json
{
  "user_id": "usr_rahul_982",
  "cart_total": 450.0,
  "per_tx_limit": 1200.0,
  "per_tx_headroom": 750.0,
  "monthly_cap": 8000.0,
  "monthly_headroom": 5750.0,
  "effective_spendable_headroom": 750.0,
  "fits_policy": true
}
```

### `POST /growth/recommendations`
Returns policy-compliant add-ons to maximize basket size.

**Response:**
```json
{
  "authorized_headroom_remaining": 750.0,
  "recommendations_count": 2,
  "recommendations": [
    {
      "id": "prod_addon_battery",
      "title": "Eco Rechargeable Battery Pack (4-Pack)",
      "price": 250.0,
      "category": "toys",
      "merchant_margin_tier": "HIGH",
      "fits_within_headroom": true,
      "projected_new_cart_total": 700.0,
      "pitch": "Frequently bought with toys. High margin (72% gross margin for merchant)."
    }
  ]
}
```

### `POST /growth/waiver/approve/{waiver_id}`
Simulates 1-tap human authorization of a single-use budget delta.
