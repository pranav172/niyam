# NIYAM Policy Schema Specification

Version: `1.0.0`  
Standard: JSON Schema Draft 2020-12 / Pydantic v2

The **NIYAM Policy Schema** defines the strict, machine-enforceable contract for spending mandates. A human operator defines policy in natural language (Hindi, English, or Hinglish); the compiler transforms it into this validated schema.

---

## 1. Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "NiyamSpendingPolicy",
  "type": "object",
  "required": ["policy_version", "user_id", "limits"],
  "properties": {
    "policy_version": {
      "type": "string",
      "description": "Semantic version or sequential identifier (e.g. v1, v2)",
      "pattern": "^v[0-9]+$"
    },
    "user_id": {
      "type": "string",
      "description": "Account holder or principal identifier"
    },
    "limits": {
      "type": "object",
      "required": ["max_per_transaction", "monthly_cap"],
      "properties": {
        "max_per_transaction": {
          "type": "number",
          "minimum": 0,
          "description": "Maximum spend allowed for a single purchase (in INR)"
        },
        "monthly_cap": {
          "type": "number",
          "minimum": 0,
          "description": "Maximum cumulative spend allowed in a rolling 30-day window (in INR)"
        },
        "category_caps": {
          "type": "object",
          "additionalProperties": {
            "type": "number",
            "minimum": 0
          },
          "description": "Spending caps per category. A cap of 0 strictly forbids the category."
        }
      }
    },
    "constraints": {
      "type": "object",
      "properties": {
        "returnable_only": {
          "type": "boolean",
          "default": false,
          "description": "If true, non-returnable items are rejected"
        },
        "cod_allowed_above": {
          "type": ["number", "null"],
          "description": "Threshold above which Cash On Delivery is permitted. If null, COD is forbidden or unconstrained."
        },
        "allowed_categories": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Explicit whitelist of product categories. If empty, all non-blocked categories are allowed."
        },
        "blocked_merchants": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Blacklist of merchant IDs or vendor tags"
        }
      }
    },
    "time_window": {
      "type": "object",
      "properties": {
        "active_hours": {
          "type": "string",
          "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]-([0-1][0-9]|2[0-3]):[0-5][0-9]$",
          "description": "Daily active window in HH:MM-HH:MM format",
          "example": "09:00-21:00"
        },
        "timezone": {
          "type": "string",
          "default": "Asia/Kolkata",
          "description": "IANA timezone identifier"
        },
        "allowed_days": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
          }
        }
      }
    }
  }
}
```

---

## 2. Real-World Examples

### Example A: "Strict Household Essentials & Kids Toys"
**Natural Language Prompt (Hinglish):**
> *"Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena. Sirf returnable items lena aur raat 9 baje ke baad shopping mat karne dena."*

**Compiled Policy JSON:**
```json
{
  "policy_version": "v1",
  "user_id": "usr_rahul_982",
  "limits": {
    "max_per_transaction": 1200,
    "monthly_cap": 8000,
    "category_caps": {
      "toys": 1500,
      "groceries": 3000,
      "electronics": 0
    }
  },
  "constraints": {
    "returnable_only": true,
    "cod_allowed_above": null,
    "allowed_categories": ["toys", "groceries", "books"],
    "blocked_merchants": []
  },
  "time_window": {
    "active_hours": "09:00-21:00",
    "timezone": "Asia/Kolkata",
    "allowed_days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
  }
}
```

---

## 3. Decision Output Schema

The evaluator strictly outputs this deterministic schema:

```json
{
  "allowed": false,
  "reason_code": "PER_TRANSACTION_LIMIT_EXCEEDED",
  "rule_fired": "limits.max_per_transaction",
  "threshold": 1200,
  "actual_value": 79999,
  "explainability": "Blocked: Total cart amount ₹79,999 exceeds maximum per-transaction limit of ₹1,200 (Delta: ₹78,799 over budget).",
  "item_evaluations": [
    {
      "product_id": "prod_phone_flagship",
      "category": "electronics",
      "price": 79999,
      "passed": false,
      "reason": "Category 'electronics' is forbidden (cap = 0)"
    }
  ]
}
```
