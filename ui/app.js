// NIYAM Mission Control Dashboard — Multi-View Architecture & Event Handlers

const DEFAULT_USER_ID = "usr_rahul_982";
const DEFAULT_AGENT_ID = "agent_shopper_01";

let currentScenarioPayload = null;
let lastExecutedPayload = null;
let lastIdempotencyKey = null;
let activeAuditFilter = "ALL";
let rawAuditLogs = [];
let activeWaiverData = null;
let lastPartialOption = null;

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
        title: "Handcrafted Wooden Teddy Bear",
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
        title: "RazorUltra Flagship 5G (256GB)",
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
  rate_limit_burst: {
    name: "Runaway Loop Rate Limit",
    agent_id: "agent_burst_demo",
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_puzzle",
        title: "Fast-Fire Loop Item",
        price: 200.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  after_hours: {
    name: "After-Hours Night Breach",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    request_timestamp: "2026-09-05T02:30:00+05:30",
    items: [
      {
        id: "prod_toy_puzzle",
        title: "MindCraft Logic 3D Puzzle",
        price: 650.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  cod_restriction: {
    name: "COD Below Minimum Threshold",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "cod",
    items: [
      {
        id: "prod_toy_clay",
        title: "Non-Toxic Modeling Clay Set",
        price: 320.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  blacklisted_merchant: {
    name: "Blacklisted Merchant Filter",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_unverified",
        title: "Discounted Action Figure (Unverified Seller)",
        price: 550.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_fraud_unverified"
      }
    ]
  },
  monthly_budget_exhausted: {
    name: "Monthly Spend Cap Exceeded",
    agent_id: DEFAULT_AGENT_ID,
    user_id: "usr_near_limit_982",
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_drone",
        title: "Educational Mini Toy Drone",
        price: 1100.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      }
    ]
  },
  atomic_split: {
    name: "Atomic Cart Split & Partial Fulfillment",
    agent_id: DEFAULT_AGENT_ID,
    user_id: DEFAULT_USER_ID,
    idempotency_key: "idemp_" + Math.random().toString(36).substring(2, 10),
    payment_method: "upi",
    items: [
      {
        id: "prod_toy_teddy",
        title: "Handcrafted Wooden Teddy Bear",
        price: 450.0,
        category: "toys",
        quantity: 1,
        returnable: true,
        cod_allowed: true,
        merchant_id: "merch_verified_toys"
      },
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
  }
};

// Application Initialization
document.addEventListener("DOMContentLoaded", () => {
  // Theme initialization
  const savedTheme = localStorage.getItem("niyam_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeButton(savedTheme);

  loadActivePolicy();
  loadScenario("happy_path");
  refreshAuditLogs();
  refreshMetrics();
  checkChaosStatus();

  // Automatic refresh interval for metrics and audit
  setInterval(() => {
    refreshAuditLogs();
    refreshMetrics();
  }, 4000);
});

// Theme Switching Logic
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("niyam_theme", newTheme);
  updateThemeButton(newTheme);
}

function updateThemeButton(theme) {
  const btn = document.getElementById("themeToggleBtn");
  if (btn) {
    btn.innerHTML = theme === "light" ? "🌙 Dark Mode" : "☀️ Light Mode";
  }
}

// Web Audio Synthesizer for Immediate Auditory Feedback
function playChime(type) {
  try {
    const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtxClass) return;
    const audioCtx = new AudioCtxClass();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    
    if (type === "approved" || type === "settled") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, audioCtx.currentTime); // C5
      osc.frequency.exponentialRampToValueAtTime(783.99, audioCtx.currentTime + 0.18); // G5
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
      osc.start(audioCtx.currentTime);
      osc.stop(audioCtx.currentTime + 0.25);
    } else if (type === "breach") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(349.23, audioCtx.currentTime); // F4
      osc.frequency.exponentialRampToValueAtTime(261.63, audioCtx.currentTime + 0.2); // C4
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
      osc.start(audioCtx.currentTime);
      osc.stop(audioCtx.currentTime + 0.25);
    }
  } catch (e) {}
}

// View Navigation Logic — Seamless Tab Switching
function switchView(viewName) {
  const views = ["commerce", "scenarios", "policy", "audit", "chaos", "playbook"];
  
  views.forEach(v => {
    const viewEl = document.getElementById(`view${v.charAt(0).toUpperCase() + v.slice(1)}`);
    const tabBtn = document.getElementById(`tab${v.charAt(0).toUpperCase() + v.slice(1)}`);
    
    if (v === viewName) {
      if (viewEl) viewEl.classList.add("active-view");
      if (tabBtn) tabBtn.classList.add("active");
    } else {
      if (viewEl) viewEl.classList.remove("active-view");
      if (tabBtn) tabBtn.classList.remove("active");
    }
  });

  if (viewName === "audit") {
    refreshAuditLogs();
  } else if (viewName === "policy") {
    loadActivePolicy();
  } else if (viewName === "commerce") {
    updateGrowthPanel();
  } else if (viewName === "chaos") {
    checkChaosStatus();
  }
}

// Load Scenario into Terminal Cart
function loadScenario(scenarioKey) {
  const sc = SCENARIOS[scenarioKey];
  if (!sc) return;

  // Generate fresh idempotency key unless testing idempotency
  if (scenarioKey !== "idempotency") {
    sc.idempotency_key = "idemp_" + Math.random().toString(36).substring(2, 10);
  }

  currentScenarioPayload = JSON.parse(JSON.stringify(sc));
  renderCartItems();
  updatePayloadViewer();

  // Reset execution result box
  const resultBox = document.getElementById("executionResultBox");
  const idleBox = document.getElementById("executionIdleBox");
  if (resultBox) resultBox.style.display = "none";
  if (idleBox) idleBox.style.display = "block";

  updateGrowthPanel();
}

// Load and immediately run scenario from Scenario Lab or Playbook
function loadAndExecuteScenario(scenarioKey) {
  switchView("commerce");
  loadScenario(scenarioKey);

  if (scenarioKey === "rate_limit_burst") {
    setTimeout(() => {
      executeRateLimitBurst();
    }, 200);
    return;
  }

  setTimeout(() => {
    executePurchase();
  }, 200);
}

// Rapid burst of requests to test TokenBucketRateLimiter live
async function executeRateLimitBurst() {
  const resultBox = document.getElementById("executionResultBox");
  const idleBox = document.getElementById("executionIdleBox");
  if (idleBox) idleBox.style.display = "none";
  if (resultBox) {
    resultBox.style.display = "block";
    resultBox.innerHTML = `
      <div class="result-card" style="border: 1px solid var(--orange); background: rgba(255, 145, 0, 0.08);">
        <div class="result-title" style="color: var(--orange);">
          <span>⚡</span> Firing Runaway Loop (12 High-Velocity Requests)...
        </div>
        <div class="result-body" style="font-size: 0.8rem; color: var(--text-secondary);">
          Simulating rogue agent loop exceeding token-bucket capacity (10 tokens).
        </div>
      </div>`;
  }

  for (let i = 1; i <= 12; i++) {
    try {
      const burstPayload = {
        ...currentScenarioPayload,
        idempotency_key: "idemp_burst_" + i + "_" + Math.random().toString(36).substring(2, 8)
      };
      const res = await fetch("/purchase", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(burstPayload)
      });
      if (res.status === 429) {
        const data = await res.json();
        playChime("breach");
        if (resultBox) {
          resultBox.innerHTML = `
            <div class="result-card result-outage">
              <div class="result-title" style="color: var(--orange);">
                <span>⏱️</span> RATE LIMITED: 429 AGENT_RATE_LIMITED (Request #${i} Throttled)
              </div>
              <div class="result-body">
                ${data.detail?.explainability || "Runaway agent loop detected and throttled."}
              </div>
              <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 0.4rem;">
                🛡️ Merchant Rail Protection Active: Token bucket exhausted at request #${i}. Retry permitted after ${data.detail?.retry_after_seconds?.toFixed(1) || "1.0"}s.
              </div>
            </div>`;
        }
        break;
      }
    } catch (e) {
      console.error(e);
    }
  }

  refreshAuditLogs();
  refreshMetrics();
}

// Render Items in Shopping Cart
function renderCartItems() {
  const container = document.getElementById("cartItemsListContainer");
  if (!container || !currentScenarioPayload) return;

  if (currentScenarioPayload.items.length === 0) {
    container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.8rem; padding: 0.8rem; text-align: center;">Cart is empty.</div>`;
    return;
  }

  container.innerHTML = currentScenarioPayload.items.map((item, index) => {
    const qty = item.quantity || 1;
    const totalItemPrice = item.price * qty;
    return `
      <div class="cart-item-card">
        <div class="cart-item-info">
          <span class="cart-item-title">${item.title}</span>
          <div class="cart-item-meta">
            <span class="badge badge-violet">${item.category}</span>
            <span>Qty: ${qty}</span>
            <span>${item.returnable ? "✓ Returnable" : "✕ Non-Returnable"}</span>
          </div>
        </div>
        <div class="cart-item-price-col">
          <span class="cart-item-price">₹${totalItemPrice.toFixed(2)}</span>
          <button class="btn-icon-danger" onclick="removeCartItem(${index})" title="Remove item">✕</button>
        </div>
      </div>
    `;
  }).join("");
}

function removeCartItem(index) {
  if (!currentScenarioPayload) return;
  currentScenarioPayload.items.splice(index, 1);
  renderCartItems();
  updatePayloadViewer();
  updateGrowthPanel();
}

function addCustomToyPrompt() {
  const name = prompt("Enter item name:", "Building Toy Blocks");
  if (!name) return;
  const priceStr = prompt("Enter price in INR:", "350");
  const price = parseFloat(priceStr) || 350.0;
  
  if (!currentScenarioPayload) {
    loadScenario("happy_path");
  }
  currentScenarioPayload.items.push({
    id: "prod_custom_" + Math.random().toString(36).substring(2, 7),
    title: name,
    price: price,
    category: "toys",
    quantity: 1,
    returnable: true,
    cod_allowed: true,
    merchant_id: "merch_verified_toys"
  });
  renderCartItems();
  updatePayloadViewer();
  updateGrowthPanel();
}

function updatePayloadViewer() {
  const viewer = document.getElementById("cartPayloadViewer");
  if (viewer && currentScenarioPayload) {
    viewer.innerText = JSON.stringify(currentScenarioPayload, null, 2);
  }
}

// Execute Purchase through NIYAM Deterministic Gateway
async function executePurchase() {
  if (!currentScenarioPayload || currentScenarioPayload.items.length === 0) {
    alert("Please add at least one item to the cart.");
    return;
  }

  const btn = document.getElementById("btnExecute");
  if (btn) {
    btn.innerText = "⏳ Evaluating Gateway...";
    btn.disabled = true;
  }

  lastExecutedPayload = JSON.parse(JSON.stringify(currentScenarioPayload));
  lastIdempotencyKey = currentScenarioPayload.idempotency_key;

  const resultBox = document.getElementById("executionResultBox");
  const idleBox = document.getElementById("executionIdleBox");
  if (idleBox) idleBox.style.display = "none";
  if (resultBox) resultBox.style.display = "block";

  try {
    const res = await fetch("/purchase", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentScenarioPayload)
    });

    const data = await res.json();

    if (res.status === 200) {
      if (data.status === "DUPLICATE_SUPPRESSED") {
        playChime("approved");
        resultBox.innerHTML = `
          <div class="result-card result-duplicate">
            <div class="result-title" style="color: #C4B5FD;">
              <span>🔁</span> Idempotency Gate (DUPLICATE_SUPPRESSED)
            </div>
            <div class="result-body" style="color: inherit;">
              ${data.message}
            </div>
            <div style="font-size: 0.72rem; color: #D8B4FE; font-family: monospace;">
              Cached Token: ${lastIdempotencyKey} | Zero Double-Debits
            </div>
          </div>`;
      } else {
        playChime("approved");
        resultBox.innerHTML = `
          <div class="result-card result-approved">
            <div class="result-title" style="color: var(--mint);">
              <span>✅</span> Transaction APPROVED by Deterministic Gate!
            </div>
            <div class="result-body" style="color: inherit;">
              ${data.explainability}
            </div>
            <div style="display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 0.5rem; align-items: center;">
              <a href="${data.payment_link}" target="_blank" class="btn btn-mint" style="font-size: 0.78rem; padding: 0.45rem 0.85rem; text-decoration: none;">
                💳 Open Razorpay Test Link (${data.razorpay_ref}) ↗
              </a>
              <button class="btn btn-secondary" style="font-size: 0.76rem; padding: 0.45rem 0.85rem;" onclick="simulateRazorpayWebhook('${data.razorpay_ref}', ${data.amount})">
                ⚡ Dispatch Webhook (Simulate Payment Settled)
              </button>
              <span style="font-size: 0.72rem; color: var(--text-muted); font-family: monospace; margin-left: auto;">
                ${data.audit_log_id}
              </span>
            </div>
          </div>`;
      }
    } else if (res.status === 403) {
      // Failure Mode 1: Policy Gate Denial
      playChime("breach");
      const err = data.detail || {};
      let waiverSnippet = "";
      let partialSnippet = "";

      if (err.save_the_sale) {
        activeWaiverData = err.save_the_sale;
        const waMode = err.save_the_sale.whatsapp_mode === "live_twilio" ? "Live Twilio" : "Sandbox Simulator";
        const phone = err.save_the_sale.recipient_phone || "+919876543210";
        const mobileUrl = err.save_the_sale.mobile_approve_url || `/growth/waiver/approve/${err.save_the_sale.waiver_id}`;
        waiverSnippet = `
          <div class="save-the-sale-banner">
            <div>
              <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom: 0.2rem;">
                <strong class="save-the-sale-title">💡 Save the Sale Opportunity:</strong>
                <span class="badge ${err.save_the_sale.whatsapp_mode === 'live_twilio' ? 'badge-mint' : 'badge-violet'}" style="font-size: 0.65rem;">${waMode}</span>
              </div>
              <div style="font-size: 0.76rem; color: var(--text-secondary);">Exceeds cap by ₹${err.save_the_sale.delta_amount.toFixed(2)}. Alert routed to ${phone}.</div>
            </div>
            <div style="display:flex; gap:0.4rem; flex-wrap: wrap;">
              <a href="${mobileUrl}" target="_blank" class="btn btn-mint" style="font-size: 0.75rem; padding: 0.4rem 0.75rem; text-decoration: none;">
                📲 1-Tap Mobile Auth ↗
              </a>
              <button class="btn btn-violet" style="font-size: 0.75rem; padding: 0.4rem 0.75rem;" onclick="openWaiverModal('${err.save_the_sale.waiver_id}', '${currentScenarioPayload.items[0]?.title || "Item"}', ${err.actual_value}, ${err.save_the_sale.delta_amount}, '${mobileUrl}', '${phone}', '${err.save_the_sale.whatsapp_mode}')">
                💬 Phone Simulator
              </button>
            </div>
          </div>
        `;

        setTimeout(() => {
          openWaiverModal(
            err.save_the_sale.waiver_id,
            currentScenarioPayload.items[0]?.title || "Robotics Building Blocks Set",
            err.actual_value,
            err.save_the_sale.delta_amount,
            mobileUrl,
            phone,
            err.save_the_sale.whatsapp_mode
          );
        }, 300);
      }

      if (err.partial_fulfillment_option && err.partial_fulfillment_option.can_fulfill_partial) {
        lastPartialOption = err.partial_fulfillment_option;
        partialSnippet = `
          <div class="partial-fulfillment-banner">
            <strong class="partial-fulfillment-title">🛒 Atomic Cart Split & Partial Fulfillment Available:</strong>
            <div style="font-size: 0.76rem; color: var(--text-secondary); margin-top: 0.2rem;">
              ${err.partial_fulfillment_option.message}
            </div>
            <button class="btn btn-mint" style="font-size: 0.75rem; padding: 0.4rem 0.8rem; margin-top: 0.5rem;" onclick="fulfillCompliantSubCart()">
              ⚡ Fulfill Compliant Items Only (₹${err.partial_fulfillment_option.compliant_subtotal.toFixed(2)})
            </button>
          </div>
        `;
      }

      resultBox.innerHTML = `
        <div class="result-card result-denied">
          <div class="result-title" style="color: var(--rose);">
            <span>🚫</span> BLOCKED by NIYAM Gate: ${err.reason_code}
          </div>
          <div class="result-body" style="color: inherit;">
            ${err.explainability}
          </div>
          <div style="font-size: 0.73rem; color: var(--text-muted); font-family: monospace;">
            Rule Fired: ${err.rule_fired} (Threshold: ₹${err.threshold} | Attempted: ₹${err.actual_value})
          </div>
          ${waiverSnippet}
          ${partialSnippet}
        </div>`;
    } else if (res.status === 429) {
      // Rate Limiting Intercept
      playChime("breach");
      const err = data.detail || {};
      resultBox.innerHTML = `
        <div class="result-card result-outage">
          <div class="result-title" style="color: var(--orange);">
            <span>⏱️</span> RATE LIMITED: ${err.status}
          </div>
          <div class="result-body">
            ${err.explainability}
          </div>
          <div style="font-size: 0.74rem; color: var(--text-muted);">
            Merchant protection active: Throttled runaway agent loop.
          </div>
        </div>`;
    } else if (res.status === 503) {
      // Failure Mode 2: Circuit Breaker Outage
      playChime("breach");
      const err = data.detail || {};
      resultBox.innerHTML = `
        <div class="result-card result-outage">
          <div class="result-title" style="color: var(--orange);">
            <span>⚠️</span> CIRCUIT BREAKER FAIL-CLOSED: ${err.reason_code}
          </div>
          <div class="result-body" style="color: inherit;">
            ${err.explainability}
          </div>
          <div style="font-size: 0.74rem; color: var(--orange);">
            Zero ghost debits. Upstream Razorpay outage safely intercepted.
          </div>
        </div>`;
    } else {
      resultBox.innerHTML = `<div style="color: var(--rose); padding: 0.6rem;">Unexpected HTTP ${res.status}: ${JSON.stringify(data)}</div>`;
    }
  } catch (err) {
    alert("Gateway connection error: " + err.message);
  } finally {
    if (btn) {
      btn.innerText = "🚀 Submit Purchase to Gateway";
      btn.disabled = false;
    }
    refreshAuditLogs();
    refreshMetrics();
  }
}

// Partial Fulfillment: Trim out breaching items and execute compliant subset
function fulfillCompliantSubCart() {
  if (!lastPartialOption || !lastPartialOption.compliant_items) return;
  currentScenarioPayload.items = JSON.parse(JSON.stringify(lastPartialOption.compliant_items));
  currentScenarioPayload.idempotency_key = "idemp_" + Math.random().toString(36).substring(2, 10);
  renderCartItems();
  updatePayloadViewer();
  executePurchase();
}

// Webhook Simulation: Triggers HMAC-signed Razorpay webhook
async function simulateRazorpayWebhook(paymentRef, amount) {
  try {
    const payload = {
      event: "payment.captured",
      payload: {
        payment: {
          entity: {
            id: paymentRef || "pay_mock_" + Math.random().toString(36).substring(2, 8),
            amount: Math.round((amount || 450) * 100),
            currency: "INR",
            status: "captured",
            notes: {
              agent_id: DEFAULT_AGENT_ID,
              user_id: DEFAULT_USER_ID
            }
          }
        }
      }
    };
    const res = await fetch("/webhooks/razorpay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      playChime("settled");
      refreshAuditLogs();
      refreshMetrics();
      alert(`Razorpay Webhook Verified: Event 'payment.captured' settled for ${paymentRef}. Transaction marked SETTLED in audit ledger!`);
    } else {
      alert("Webhook dispatch error");
    }
  } catch (err) {
    alert("Webhook dispatch error: " + err.message);
  }
}

// Retry identical idempotency payload
function retryLastPurchase() {
  if (!lastExecutedPayload) {
    alert("Submit a purchase first before testing idempotency retry.");
    return;
  }
  currentScenarioPayload = JSON.parse(JSON.stringify(lastExecutedPayload));
  renderCartItems();
  updatePayloadViewer();
  executePurchase();
}

// WhatsApp 1-Tap Modal Control
function openWaiverModal(waiverId, itemTitle, cartTotal, delta, mobileUrl, phone, mode) {
  activeWaiverData = { waiverId, itemTitle, cartTotal, delta, mobileUrl, phone, mode };
  
  const modal = document.getElementById("saveTheSaleModal");
  const titleEl = document.getElementById("waItemTitle");
  const totalEl = document.getElementById("waCartTotal");
  const approvedBubble = document.getElementById("waBubbleApproved");
  const approveBtn = document.getElementById("btnWaApprove");
  const modeBadge = document.getElementById("waModeBadge");
  const linkBtn = document.getElementById("waMobileLinkBtn");
  const phoneEl = document.getElementById("waRecipientPhone");

  if (titleEl) titleEl.innerText = itemTitle;
  if (totalEl) totalEl.innerText = `₹${cartTotal.toFixed(2)}`;
  if (phoneEl && phone) phoneEl.innerText = phone;
  if (modeBadge && mode) {
    modeBadge.innerText = mode === "live_twilio" ? "Live Twilio WhatsApp" : "Sandbox Simulator";
    modeBadge.className = mode === "live_twilio" ? "badge badge-mint" : "badge badge-volt";
  }
  if (linkBtn && mobileUrl) {
    linkBtn.href = mobileUrl;
  }
  if (approvedBubble) approvedBubble.style.display = "none";
  if (approveBtn) {
    approveBtn.disabled = false;
    approveBtn.innerText = "⚡ 1-Tap Authorize Exception (WhatsApp)";
  }

  if (modal) modal.style.display = "flex";
}

function closeWaiverModal() {
  const modal = document.getElementById("saveTheSaleModal");
  if (modal) modal.style.display = "none";
}

async function approveWaiverFromModal() {
  if (!activeWaiverData || !activeWaiverData.waiverId) return;
  const approveBtn = document.getElementById("btnWaApprove");
  const approvedBubble = document.getElementById("waBubbleApproved");

  if (approveBtn) {
    approveBtn.innerText = "⏳ Authorizing...";
    approveBtn.disabled = true;
  }

  try {
    const res = await fetch(`/growth/waiver/approve/${activeWaiverData.waiverId}`, { method: "POST" });
    if (res.ok) {
      if (approvedBubble) approvedBubble.style.display = "block";
      playChime("approved");

      setTimeout(async () => {
        closeWaiverModal();
        currentScenarioPayload.waiver_id = activeWaiverData.waiverId;
        updatePayloadViewer();
        await executePurchase();
      }, 700);
    } else {
      alert("Waiver authorization failed");
      if (approveBtn) approveBtn.disabled = false;
    }
  } catch (err) {
    alert("Waiver network error: " + err.message);
  }
}

function rejectWaiverFromModal() {
  closeWaiverModal();
  alert("Waiver rejected by Principal. Transaction remains blocked at the gate.");
}

// Headroom & Upsell Recommendations
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
      const headroom = data.authorized_headroom_remaining || 0;

      const headroomEl = document.getElementById("headroomAmountText");
      if (headroomEl) {
        headroomEl.innerText = `₹${headroom.toFixed(2)} Available`;
        headroomEl.style.color = headroom > 0 ? "var(--mint)" : "var(--rose)";
      }

      const bar = document.getElementById("headroomProgressBar");
      if (bar) {
        const pct = Math.min(100, Math.max(0, (cartTotal / 1200) * 100));
        bar.style.width = `${pct}%`;
        bar.style.background = pct > 100 ? "var(--rose)" : "linear-gradient(90deg, var(--mint), var(--volt))";
      }

      const container = document.getElementById("upsellButtonsContainer");
      if (container) {
        if (!data.recommendations || data.recommendations.length === 0) {
          container.innerHTML = '<span style="font-size:0.75rem; color: var(--text-muted);">No add-ons fit remaining headroom.</span>';
        } else {
          container.innerHTML = data.recommendations.slice(0, 3).map(r => `
            <button class="upsell-chip-btn" onclick="addUpsellToCart('${r.id}', '${r.title}', ${r.price}, '${r.category}')">
              <span>➕</span> ${r.title} (+₹${r.price})
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
    cod_allowed: true,
    merchant_id: "merch_growth_partner"
  });
  currentScenarioPayload.idempotency_key = "idemp_" + Math.random().toString(36).substring(2, 10);
  renderCartItems();
  updatePayloadViewer();
  updateGrowthPanel();
}

// Policy Studio Handlers
async function loadActivePolicy() {
  try {
    const res = await fetch(`/policies/${DEFAULT_USER_ID}`);
    if (res.ok) {
      const data = await res.json();
      const policy = data.active_policy;

      const badge = document.getElementById("activePolicyVersionBadge");
      if (badge) badge.innerText = policy.policy_version;

      const tag = document.getElementById("activePolicyTag");
      if (tag) tag.innerText = `Policy ${policy.policy_version} Active`;

      const viewer = document.getElementById("policyJsonViewer");
      if (viewer) viewer.innerText = JSON.stringify(policy, null, 2);
    }
  } catch (err) {
    console.error("Error loading policy:", err);
  }
}

function setPolicyTemplate(type) {
  const input = document.getElementById("policyInput");
  if (!input) return;

  if (type === "toys") {
    input.value = "Baccho ke toys ke liye max 1200 per order, electronics bilkul nahi, monthly 8000 se upar mat hone dena. Sirf returnable items lena.";
  } else if (type === "strict") {
    input.value = "Electronics aur gadgets strictly banned hai. Max 500 per transaction, monthly limit 3000. Books aur stationeries only.";
  } else if (type === "festival") {
    input.value = "Festival shopping: Max 5000 per order across toys, home, and clothing. No electronics. Monthly cap 25000. Returnable only.";
  } else if (type === "conservative") {
    input.value = "Safety mode: Strict cap of 500 per order, only returnable items allowed, electronics zero cap. Monthly budget 2000.";
  }
}

async function compilePolicy() {
  const input = document.getElementById("policyInput");
  const promptText = input ? input.value : "";
  if (!promptText.trim()) return;

  const btn = document.getElementById("btnCompilePolicy");
  if (btn) {
    btn.innerText = "⏳ Compiling Policy Contract...";
    btn.disabled = true;
  }

  try {
    const res = await fetch("/policies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: DEFAULT_USER_ID, prompt: promptText })
    });
    const data = await res.json();
    if (res.ok) {
      const badge = document.getElementById("activePolicyVersionBadge");
      if (badge) badge.innerText = data.policy.policy_version;

      const tag = document.getElementById("activePolicyTag");
      if (tag) tag.innerText = `Policy ${data.policy.policy_version} Active`;

      const viewer = document.getElementById("policyJsonViewer");
      if (viewer) viewer.innerText = JSON.stringify(data.policy, null, 2);

      refreshAuditLogs();
      refreshMetrics();
      playChime("approved");
      alert(`Policy ${data.policy.policy_version} compiled and activated successfully!`);
    } else {
      alert("Policy Compilation Error: " + (data.detail || "Validation failed"));
    }
  } catch (err) {
    alert("Connection error: " + err.message);
  } finally {
    if (btn) {
      btn.innerText = "⚡ Compile & Activate New Policy Version (vN+1)";
      btn.disabled = false;
    }
  }
}

// Live Audit Ledger Forensics
async function refreshAuditLogs() {
  try {
    const res = await fetch("/audit/logs?limit=50");
    if (!res.ok) return;
    const data = await res.json();
    rawAuditLogs = data.logs || [];
    renderFilteredAuditLogs();
  } catch (err) {
    console.error("Error refreshing audit logs:", err);
  }
}

function filterAuditLogs(filterType) {
  activeAuditFilter = filterType;
  
  document.querySelectorAll(".filter-pill").forEach(el => {
    if (el.innerText.toUpperCase().includes(filterType) || (filterType === "ALL" && el.innerText === "All")) {
      el.classList.add("active");
    } else {
      el.classList.remove("active");
    }
  });

  renderFilteredAuditLogs();
}

function renderFilteredAuditLogs() {
  const container = document.getElementById("auditListContainer");
  if (!container) return;

  let logs = rawAuditLogs;
  if (activeAuditFilter !== "ALL") {
    logs = logs.filter(l => l.action === activeAuditFilter);
  }

  if (logs.length === 0) {
    container.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 1.2rem; text-align: center;">No audit events match current filter.</div>';
    return;
  }

  container.innerHTML = logs.map(log => {
    let badgeClass = "badge-violet";
    let actionLabel = log.action;
    if (log.action === "APPROVED") badgeClass = "badge-mint";
    else if (log.action === "DENIED") badgeClass = "badge-rose";
    else if (log.action === "DUPLICATE_SUPPRESSED") badgeClass = "badge-violet";
    else if (log.action === "RAZORPAY_UNAVAILABLE") badgeClass = "badge-orange";
    else if (log.action === "SETTLED") badgeClass = "badge-mint";
    else if (log.action === "RATE_LIMITED") badgeClass = "badge-orange";

    const timeStr = new Date(log.ts).toLocaleTimeString();
    const amountStr = log.amount > 0 ? `₹${log.amount.toLocaleString("en-IN")}` : "";

    let linkHtml = "";
    if (log.razorpay_ref) {
      linkHtml = `
        <div style="margin-top: 0.2rem;">
          <a href="https://rzp.io/i/test_${log.razorpay_ref.slice(-6)}" target="_blank" style="color: var(--mint); font-size: 0.74rem; text-decoration: none;">
            💳 Razorpay Ref: ${log.razorpay_ref} ↗
          </a>
        </div>`;
    }

    let ruleTag = "";
    if (log.decision && log.decision.rule_fired) {
      ruleTag = `<span class="audit-rule-code">${log.decision.rule_fired}</span>`;
    } else if (log.decision && log.decision.reason_code) {
      ruleTag = `<span class="audit-rule-code">${log.decision.reason_code}</span>`;
    }

    return `
      <div class="audit-card-item">
        <div class="audit-meta-row">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span class="badge ${badgeClass}">${actionLabel}</span>
            ${amountStr ? `<strong style="font-size: 0.85rem; color: var(--text-primary);">${amountStr}</strong>` : ""}
          </div>
          <span style="font-size: 0.74rem; color: var(--text-muted);">${timeStr}</span>
        </div>
        <div style="font-size: 0.82rem; line-height: 1.45; color: inherit;">
          ${log.explainability}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          ${ruleTag}
          <span style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace;">${log.id}</span>
        </div>
        ${linkHtml}
      </div>
    `;
  }).join("");
}

// Export Audit Trail as CSV
function exportAuditCsv() {
  const btn = document.getElementById("btnExportCsv");
  if (btn) {
    btn.innerText = "⏳ Downloading...";
  }
  window.location.href = "/audit/export?format=csv";
  setTimeout(() => {
    if (btn) btn.innerText = "📥 Export Compliance CSV";
  }, 1200);
}

// Export Audit Trail as PDF / Print
function exportAuditPdf() {
  switchView("audit");
  setTimeout(() => {
    window.print();
  }, 300);
}

// Circuit Breaker & Chaos Engineering
async function toggleChaos(enabled) {
  try {
    const res = await fetch("/chaos/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled })
    });
    const data = await res.json();
    updateChaosUI(enabled);
  } catch (err) {
    console.error("Chaos toggle error:", err);
  }
}

function toggleChaosFromLab() {
  const toggle = document.getElementById("chaosToggle");
  if (toggle) {
    toggle.checked = !toggle.checked;
    toggleChaos(toggle.checked);
  }
}

function updateChaosUI(isOpen) {
  const badge = document.getElementById("chaosStatusBadge");
  const labState = document.getElementById("chaosLabState");
  const labBtn = document.getElementById("btnChaosLabToggle");
  const toggle = document.getElementById("chaosToggle");
  const machineBadge = document.getElementById("circuitMachineBadge");
  const nodeClosed = document.getElementById("nodeClosed");
  const nodeOpen = document.getElementById("nodeOpen");

  if (toggle) toggle.checked = isOpen;

  if (isOpen) {
    if (badge) {
      badge.className = "chaos-indicator ind-open";
      badge.innerText = "OUTAGE ACTIVE (OPEN)";
    }
    if (machineBadge) {
      machineBadge.className = "badge badge-orange";
      machineBadge.innerText = "TRIPPED (OPEN)";
    }
    if (labState) {
      labState.innerText = "OPEN (Outage Active)";
      labState.style.color = "var(--orange)";
    }
    if (labBtn) {
      labBtn.innerText = "✅ Restore Normal Connection";
      labBtn.className = "btn btn-secondary";
    }
    if (nodeClosed) {
      nodeClosed.classList.remove("active-node");
    }
    if (nodeOpen) {
      nodeOpen.classList.add("active-node", "node-open");
    }
  } else {
    if (badge) {
      badge.className = "chaos-indicator ind-closed";
      badge.innerText = "CIRCUIT CLOSED";
    }
    if (machineBadge) {
      machineBadge.className = "badge badge-mint";
      machineBadge.innerText = "HEALTHY (CLOSED)";
    }
    if (labState) {
      labState.innerText = "CLOSED (Healthy)";
      labState.style.color = "var(--mint)";
    }
    if (labBtn) {
      labBtn.innerText = "💥 Trip Circuit Breaker";
      labBtn.className = "btn btn-orange";
    }
    if (nodeClosed) {
      nodeClosed.classList.add("active-node");
    }
    if (nodeOpen) {
      nodeOpen.classList.remove("active-node", "node-open");
    }
  }
}

async function checkChaosStatus() {
  try {
    const res = await fetch("/chaos/status");
    if (res.ok) {
      const data = await res.json();
      updateChaosUI(data.chaos_mode);
    }
  } catch (err) {}
}

async function testOutagePurchase() {
  const toggle = document.getElementById("chaosToggle");
  if (!toggle.checked) {
    toggle.checked = true;
    await toggleChaos(true);
  }
  loadAndExecuteScenario("happy_path");
}

// Quick Metrics
async function refreshMetrics() {
  try {
    const res = await fetch("/audit/metrics");
    if (!res.ok) return;
    const m = await res.json();
    
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val;
    };

    setVal("mTotalEvals", m.total_evaluations || 0);
    setVal("mApproved", m.approved_count || 0);
    setVal("mDenied", m.denied_count || 0);
    setVal("mDuplicates", m.duplicate_suppressed_count || 0);
    setVal("mCircuitBreaker", m.circuit_breaker_tripped_count || 0);
  } catch (err) {}
}

// Global Refresh
function refreshAll() {
  loadActivePolicy();
  refreshAuditLogs();
  refreshMetrics();
  checkChaosStatus();
  updateGrowthPanel();
}
