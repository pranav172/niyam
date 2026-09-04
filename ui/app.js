// NIYAM Mission Control Dashboard Application Logic

const DEFAULT_USER_ID = "usr_rahul_982";
const DEFAULT_AGENT_ID = "agent_shopper_01";

let currentScenarioPayload = null;
let lastExecutedPayload = null;
let lastIdempotencyKey = null;

// Pre-defined scenarios
const SCENARIOS = {
  happy_path: {
    name: "Compliant Purchase",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_teddy",
        title: "Wooden Handcrafted Teddy Bear",
        price: 450.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  overspend: {
    name: "Failure Mode 1: Overspend Breach",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_phone_flagship",
        title: "RazorUltra Flagship 5G",
        price: 79999.0,
        category: "electronics",
        quantity: 1,
        returnable: true,
        cod_allowed: false,
        merchant_id: "merch_electronic_hub"
      }
    ]
  },
  forbidden_cat: {
    name: "Failure Mode 1: Forbidden Category",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_wireless_earbuds",
        title: "True Wireless Earbuds",
        price: 899.0,
        category: "electronics",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_electronic_hub"
      }
    ]
  },
  non_returnable: {
    name: "Failure Mode 1: Non-Returnable Item",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_custom_doll",
        title: "Custom Engraved Name Doll",
        price: 600.0,
        category: "toys",
        quantity: 1,
        returnable: false,
        cod_allowed: false,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  idempotency: {
    name: "Idempotency Test",
    // Uses last executed payload or happy path with fixed key
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_fixed_retry_demo_key",
    payment_method: "upi",
    items: [
      {
        id: "prod_kids_encyclopedia",
        title: "Science & Space Encyclopedia",
        price: 420.0,
        category: "books",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_book_store"
      }
    ]
  },
  chaos: {
    name: "Failure Mode 2: Razorpay Outage",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_teddy",
        title: "Wooden Handcrafted Teddy Bear",
        price: 450.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  marginal_overspend: {
    name: "Save the Sale (1-Tap Waiver)",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_lego",
        title: "Robotics Building Blocks Set",
        price: 1350.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  }
};

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  loadActivePolicy();
  loadScenario("happy_path");
  refreshAuditLogs();
  refreshMetrics();
  checkChaosStatus();

  // Polling loop
  setInterval(() => {
    refreshAuditLogs();
    refreshMetrics();
  }, 3000);
});

async function loadActivePolicy() {
  try {
    const res = await fetch(`/policies/${DEFAULT_USER_ID}`);
    if (res.ok) {
      const data = await res.json();
      const policy = data.active_policy;
      document.getElementById("activePolicyVersionBadge").innerText = policy.policy_version;
      document.getElementById("policyJsonViewer").innerText = JSON.stringify(policy, null, 2);
    }
  } catch (err) {
    console.error("Error loading policy:", err);
  }
}

async function compilePolicy() {
  const promptText = document.getElementById("policyInput").value;
  if (!promptText.trim()) return;

  try {
    const res = await fetch("/policies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: DEFAULT_USER_ID, prompt: promptText })
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById("activePolicyVersionBadge").innerText = data.policy.policy_version;
      document.getElementById("policyJsonViewer").innerText = JSON.stringify(data.policy, null, 2);
      refreshAuditLogs();
      refreshMetrics();
    } else {
      alert("Policy Compilation Error: " + (data.detail || "Validation failed"));
    }
  } catch (err) {
    alert("Connection error: " + err.message);
  }
}

function loadScenario(scenarioKey) {
  const sc = SCENARIOS[scenarioKey];
  if (!sc) return;

  // Generate fresh idempotency key unless testing idempotency
  if (scenarioKey !== "idempotency") {
    sc.idempotency_key = "idemp_" + Math.random().toString(36).substring(2, 10);
  }

  currentScenarioPayload = JSON.parse(JSON.stringify(sc));
  document.getElementById("cartPayloadViewer").innerText = JSON.stringify(currentScenarioPayload, null, 2);
  
  // If scenario is chaos, automatically activate the chaos switch
  if (scenarioKey === "chaos") {
    document.getElementById("chaosToggle").checked = true;
    toggleChaos(true);
  } else {
    document.getElementById("chaosToggle").checked = false;
    toggleChaos(false);
  }

  updateGrowthPanel();
}

async function executePurchase() {
  if (!currentScenarioPayload) return;
  const btn = document.getElementById("btnExecute");
  btn.innerText = "⏳ Evaluating...";
  btn.disabled = true;

  lastExecutedPayload = JSON.parse(JSON.stringify(currentScenarioPayload));
  lastIdempotencyKey = currentScenarioPayload.idempotency_key;

  try {
    const res = await fetch("/purchase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentScenarioPayload)
    });

    const data = await res.json();
    const resultBox = document.getElementById("executionResultBox");
    resultBox.style.display = "block";

    if (res.status === 200) {
      if (data.status === "DUPLICATE_SUPPRESSED") {
        resultBox.innerHTML = `
          <div style="background: rgba(139, 92, 246, 0.15); border: 1px solid #8B5CF6; border-radius: 8px; padding: 0.8rem; margin-top: 0.8rem;">
            <strong style="color: #A78BFA;">🔁 Idempotency Gate (DUPLICATE_SUPPRESSED):</strong><br>
            <span style="font-size: 0.82rem; color: #DDD6FE;">${data.message}</span>
          </div>`;
      } else {
        resultBox.innerHTML = `
          <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 8px; padding: 0.8rem; margin-top: 0.8rem;">
            <strong style="color: #34D399;">✅ Transaction APPROVED by Deterministic Gate!</strong><br>
            <span style="font-size: 0.82rem; color: #A7F3D0;">${data.explainability}</span><br>
            <div style="margin-top: 0.5rem;">
              <a href="${data.payment_link}" target="_blank" class="audit-ref-link" style="color: #38BDF8;">
                🔗 Open Razorpay Test Payment Link (${data.razorpay_ref}) ↗
              </a>
            </div>
          </div>`;
      }
      hideEscalation();
    } else if (res.status === 403) {
      // Failure Mode 1: Deterministic Denial
      const err = data.detail || {};
      let waiverHtml = "";
      if (err.save_the_sale) {
        waiverHtml = `
          <div style="margin-top: 0.6rem; padding: 0.8rem; background: rgba(14, 165, 233, 0.15); border: 1px solid #0EA5E9; border-radius: 8px;">
            <strong style="color: #38BDF8;">💡 "Save the Sale" Conversion Recovery:</strong><br>
            <span style="font-size: 0.8rem; color: #BAE6FD;">
              Purchase exceeds limit by ₹${err.save_the_sale.delta_amount.toFixed(2)}. As the account principal, you can authorize this one-time purchase with 1-tap:
            </span><br>
            <button class="btn" style="margin-top: 0.6rem; background: #0284C7; font-size: 0.78rem; padding: 0.45rem 0.9rem;" onclick="approveWaiverAndRetry('${err.save_the_sale.waiver_id}')">
              📲 1-Tap Authorize Exception via WhatsApp / Push ↗
            </button>
          </div>
        `;
      }
      resultBox.innerHTML = `
        <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid #EF4444; border-radius: 8px; padding: 0.8rem; margin-top: 0.8rem;">
          <strong style="color: #F87171;">🚫 BLOCKED by NIYAM Gate: ${err.reason_code}</strong><br>
          <span style="font-size: 0.82rem; color: #FECACA;">${err.explainability}</span><br>
          <span style="font-size: 0.75rem; color: #94A3B8; font-family: monospace;">Rule Fired: ${err.rule_fired} (Threshold: ₹${err.threshold} | Actual: ₹${err.actual_value})</span>
          ${waiverHtml}
        </div>`;
      showEscalation(err.explainability);
    } else if (res.status === 503) {
      // Failure Mode 2: Circuit Breaker Intercept
      const err = data.detail || {};
      resultBox.innerHTML = `
        <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid #F59E0B; border-radius: 8px; padding: 0.8rem; margin-top: 0.8rem;">
          <strong style="color: #FBBF24;">⚠️ CIRCUIT BREAKER FAIL-CLOSED: ${err.reason_code}</strong><br>
          <span style="font-size: 0.82rem; color: #FDE68A;">${err.explainability}</span><br>
          <span style="font-size: 0.75rem; color: #FCD34D;">Zero money moved. Upstream Razorpay outage safely intercepted.</span>
        </div>`;
      showEscalation("Payment rails unavailable. Circuit breaker fail-closed initiated.");
    } else {
      resultBox.innerHTML = `<div style="color: red; padding: 0.5rem;">Unexpected response: ${res.status}</div>`;
    }

  } catch (err) {
    alert("Execution error: " + err.message);
  } finally {
    btn.innerText = "🚀 Submit Purchase to Gateway";
    btn.disabled = false;
    refreshAuditLogs();
    refreshMetrics();
  }
}

function retryLastPurchase() {
  if (!lastExecutedPayload) {
    alert("Execute a purchase first before retrying!");
    return;
  }
  // Keep the exact same idempotency key
  currentScenarioPayload = JSON.parse(JSON.stringify(lastExecutedPayload));
  document.getElementById("cartPayloadViewer").innerText = JSON.stringify(currentScenarioPayload, null, 2);
  executePurchase();
}

async function approveWaiverAndRetry(waiverId) {
  try {
    const res = await fetch(`/growth/waiver/approve/${waiverId}`, { method: "POST" });
    if (res.ok) {
      // Re-submit purchase with approved waiver_id attached
      currentScenarioPayload.waiver_id = waiverId;
      document.getElementById("cartPayloadViewer").innerText = JSON.stringify(currentScenarioPayload, null, 2);
      await executePurchase();
    } else {
      alert("Failed to approve waiver");
    }
  } catch (err) {
    alert("Waiver approval error: " + err.message);
  }
}

async function updateGrowthPanel() {
  if (!currentScenarioPayload) return;
  const cartTotal = currentScenarioPayload.items.reduce((s, i) => s + (i.price * (i.quantity || 1)), 0);
  try {
    const res = await fetch("/growth/recommendations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: DEFAULT_USER_ID, cart_total: cartTotal })
    });
    if (res.ok) {
      const data = await res.json();
      const headroomEl = document.getElementById("headroomAmountText");
      if (headroomEl) {
        headroomEl.innerText = `₹${data.authorized_headroom_remaining.toFixed(2)} Available`;
        headroomEl.style.color = data.authorized_headroom_remaining > 0 ? "var(--success)" : "var(--danger)";
      }

      const container = document.getElementById("upsellButtonsContainer");
      if (container) {
        if (!data.recommendations || data.recommendations.length === 0) {
          container.innerHTML = '<span style="font-size:0.75rem; color: #64748B;">No add-ons fit remaining headroom.</span>';
        } else {
          container.innerHTML = data.recommendations.slice(0, 2).map(r => `
            <button class="btn btn-secondary" style="font-size: 0.72rem; padding: 0.35rem 0.6rem;" onclick="addUpsellToCart('${r.id}', '${r.title}', ${r.price}, '${r.category}')">
              ➕ ${r.title} (+₹${r.price})
            </button>
          `).join("");
        }
      }
    }
  } catch (err) {}
}

function addUpsellToCart(id, title, price, category) {
  if (!currentScenarioPayload) return;
  currentScenarioPayload.items.push({
    id: id,
    title: title,
    price: price,
    category: category,
    quantity: 1,
    returnable: true,
    cod_allowed: true
  });
  // Recalculate total
  currentScenarioPayload.idempotency_key = "idemp_" + Math.random().toString(36).substring(2, 10);
  document.getElementById("cartPayloadViewer").innerText = JSON.stringify(currentScenarioPayload, null, 2);
  updateGrowthPanel();
}

async function toggleChaos(enabled) {
  try {
    const res = await fetch("/chaos/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled })
    });
    const data = await res.json();
    const badge = document.getElementById("chaosStatusBadge");
    if (enabled) {
      badge.className = "chaos-status status-outage";
      badge.innerText = "OUTAGE ACTIVE (OPEN)";
    } else {
      badge.className = "chaos-status status-normal";
      badge.innerText = "CIRCUIT CLOSED";
    }
  } catch (err) {
    console.error("Chaos toggle error:", err);
  }
}

async function checkChaosStatus() {
  try {
    const res = await fetch("/chaos/status");
    if (res.ok) {
      const data = await res.json();
      document.getElementById("chaosToggle").checked = data.chaos_mode;
      const badge = document.getElementById("chaosStatusBadge");
      if (data.chaos_mode) {
        badge.className = "chaos-status status-outage";
        badge.innerText = "OUTAGE ACTIVE (OPEN)";
      } else {
        badge.className = "chaos-status status-normal";
        badge.innerText = "CIRCUIT CLOSED";
      }
    }
  } catch (err) {}
}

async function refreshAuditLogs() {
  try {
    const res = await fetch("/audit/logs?limit=25");
    if (!res.ok) return;
    const data = await res.json();
    const container = document.getElementById("auditListContainer");
    if (!data.logs || data.logs.length === 0) {
      container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem;">No events recorded yet.</div>';
      return;
    }

    container.innerHTML = data.logs.map(log => {
      let badgeClass = "badge-policy";
      let actionLabel = log.action;
      if (log.action === "APPROVED") badgeClass = "badge-approved";
      else if (log.action === "DENIED") badgeClass = "badge-denied";
      else if (log.action === "DUPLICATE_SUPPRESSED") badgeClass = "badge-duplicate";
      else if (log.action === "RAZORPAY_UNAVAILABLE") badgeClass = "badge-outage";

      const timeStr = new Date(log.ts).toLocaleTimeString();
      const amountStr = log.amount > 0 ? `₹${log.amount.toLocaleString("en-IN")}` : "";

      let linkHtml = "";
      if (log.razorpay_ref) {
        linkHtml = `
          <div style="margin-top: 0.3rem;">
            <a href="https://rzp.io/i/test_${log.razorpay_ref.slice(-6)}" target="_blank" class="audit-ref-link">
              💳 Razorpay Ref: ${log.razorpay_ref} ↗
            </a>
          </div>`;
      }

      let ruleTag = "";
      if (log.decision && log.decision.rule_fired) {
        ruleTag = `<span class="audit-rule-tag">${log.decision.rule_fired}</span>`;
      } else if (log.decision && log.decision.reason_code) {
        ruleTag = `<span class="audit-rule-tag">${log.decision.reason_code}</span>`;
      }

      return `
        <div class="audit-entry">
          <div class="audit-entry-top">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="badge ${badgeClass}">${actionLabel}</span>
              ${amountStr ? `<strong style="font-size: 0.8rem;">${amountStr}</strong>` : ""}
            </div>
            <span class="audit-time">${timeStr}</span>
          </div>
          <div class="audit-explain">${log.explainability}</div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.2rem;">
            ${ruleTag}
            <span style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace;">${log.id}</span>
          </div>
          ${linkHtml}
        </div>
      `;
    }).join("");

  } catch (err) {
    console.error("Error refreshing audit logs:", err);
  }
}

async function refreshMetrics() {
  try {
    const res = await fetch("/audit/metrics");
    if (!res.ok) return;
    const m = await res.json();
    document.getElementById("mTotalEvals").innerText = m.total_evaluations || 0;
    document.getElementById("mApproved").innerText = m.approved_count || 0;
    document.getElementById("mDenied").innerText = m.denied_count || 0;
    document.getElementById("mDuplicates").innerText = m.duplicate_suppressed_count || 0;
    document.getElementById("mCircuitBreaker").innerText = m.circuit_breaker_tripped_count || 0;
    document.getElementById("mCompliance").innerText = m.compliance_rate || "100%";
  } catch (err) {}
}

function showEscalation(text) {
  const el = document.getElementById("escalationNotification");
  document.getElementById("escalationText").innerText = text;
  el.style.display = "flex";
}

function hideEscalation() {
  document.getElementById("escalationNotification").style.display = "none";
}

function refreshAll() {
  loadActivePolicy();
  refreshAuditLogs();
  refreshMetrics();
  checkChaosStatus();
}
