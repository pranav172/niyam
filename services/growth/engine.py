"""NIYAM Growth & Revenue Optimization Engine
Implements:
1. Policy-Aware Upsell Engine (Grows Merchant Average Order Value / AOV within policy bounds)
2. Authorized Headroom Analysis (Computes maximum spend headroom without violating constraints)
3. 'Save the Sale' 1-Tap Policy Waiver Manager (Recovers lost conversions on marginal budget breaches)
"""
import uuid
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from services.compiler.schema import SpendingPolicy, PurchaseRequest, PurchaseItem, UserSpendState


class HeadroomAnalysis(BaseModel):
    user_id: str
    cart_total: float
    per_tx_limit: float
    per_tx_headroom: float
    monthly_cap: float
    monthly_spend_accumulated: float
    monthly_headroom: float
    effective_spendable_headroom: float
    fits_policy: bool


class UpsellItem(BaseModel):
    id: str
    title: str
    price: float
    category: str
    merchant_margin_tier: str  # HIGH, MEDIUM, STRATEGIC
    fits_within_headroom: bool
    projected_new_cart_total: float
    pitch: str


class PolicyWaiver(BaseModel):
    waiver_id: str
    user_id: str
    agent_id: str
    cart_total: float
    policy_limit: float
    delta_amount: float
    reason: str
    status: str  # PENDING, APPROVED, REJECTED, EXPIRED
    created_at: float
    expires_at: float
    approved_at: Optional[float] = None


# High-margin add-on catalog designed to boost merchant revenue
UPSELL_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "prod_addon_battery",
        "title": "Eco Rechargeable Battery Pack (4-Pack)",
        "price": 250.0,
        "category": "toys",
        "merchant_margin_tier": "HIGH",
        "pitch": "Frequently bought with toys. High margin (72% gross margin for merchant)."
    },
    {
        "id": "prod_addon_gift_wrap",
        "title": "Artisanal Gift Wrapping & Handwritten Card",
        "price": 120.0,
        "category": "toys",
        "merchant_margin_tier": "HIGH",
        "pitch": "Zero-inventory upsell. 90% margin for gifting orders."
    },
    {
        "id": "prod_addon_cleaning_kit",
        "title": "Toy & Gadget Natural Sanitizing Spray",
        "price": 180.0,
        "category": "groceries",
        "merchant_margin_tier": "MEDIUM",
        "pitch": "Safe natural spray for kids toys and surfaces."
    },
    {
        "id": "prod_addon_bookmark_set",
        "title": "Metallic Astronomy Bookmarks (Set of 3)",
        "price": 150.0,
        "category": "books",
        "merchant_margin_tier": "HIGH",
        "pitch": "Complementary book accessory with high merchant markup."
    }
]


class WaiverManager:
    """Manages dynamic single-use policy waivers for 'Save the Sale' conversion recovery."""

    def __init__(self, ttl_seconds: float = 900.0):  # 15 minutes default TTL
        self.ttl_seconds = ttl_seconds
        self._waivers: Dict[str, PolicyWaiver] = {}

    def request_waiver(
        self,
        user_id: str,
        agent_id: str,
        cart_total: float,
        policy_limit: float,
        reason: str
    ) -> PolicyWaiver:
        waiver_id = f"wvr_{uuid.uuid4().hex[:10]}"
        now = time.time()
        delta = max(0.0, cart_total - policy_limit)

        waiver = PolicyWaiver(
            waiver_id=waiver_id,
            user_id=user_id,
            agent_id=agent_id,
            cart_total=cart_total,
            policy_limit=policy_limit,
            delta_amount=delta,
            reason=reason,
            status="PENDING",
            created_at=now,
            expires_at=now + self.ttl_seconds
        )
        self._waivers[waiver_id] = waiver
        return waiver

    def approve_waiver(self, waiver_id: str) -> Optional[PolicyWaiver]:
        waiver = self._waivers.get(waiver_id)
        if not waiver:
            return None
        if time.time() > waiver.expires_at:
            waiver.status = "EXPIRED"
            return waiver

        waiver.status = "APPROVED"
        waiver.approved_at = time.time()
        return waiver

    def reject_waiver(self, waiver_id: str) -> Optional[PolicyWaiver]:
        waiver = self._waivers.get(waiver_id)
        if not waiver:
            return None
        waiver.status = "REJECTED"
        return waiver

    def get_waiver(self, waiver_id: str) -> Optional[PolicyWaiver]:
        waiver = self._waivers.get(waiver_id)
        if waiver and waiver.status == "PENDING" and time.time() > waiver.expires_at:
            waiver.status = "EXPIRED"
        return waiver


class GrowthEngine:
    """Analyzes cart headroom and suggests policy-compliant upsells to grow merchant GMV."""

    def __init__(self):
        self.waiver_manager = WaiverManager()

    def calculate_headroom(
        self,
        policy: SpendingPolicy,
        cart_total: float,
        spend_state: Optional[UserSpendState] = None
    ) -> HeadroomAnalysis:
        if spend_state is None:
            spend_state = UserSpendState(user_id=policy.user_id)

        per_tx_headroom = max(0.0, policy.limits.max_per_transaction - cart_total)
        current_monthly = spend_state.monthly_spend_accumulated
        monthly_headroom = max(0.0, policy.limits.monthly_cap - (current_monthly + cart_total))
        
        # Effective headroom is constrained by both transaction cap and monthly budget
        effective_headroom = min(per_tx_headroom, monthly_headroom)
        fits_policy = cart_total <= policy.limits.max_per_transaction and (current_monthly + cart_total) <= policy.limits.monthly_cap

        return HeadroomAnalysis(
            user_id=policy.user_id,
            cart_total=cart_total,
            per_tx_limit=policy.limits.max_per_transaction,
            per_tx_headroom=per_tx_headroom,
            monthly_cap=policy.limits.monthly_cap,
            monthly_spend_accumulated=current_monthly,
            monthly_headroom=monthly_headroom,
            effective_spendable_headroom=effective_headroom,
            fits_policy=fits_policy
        )

    def recommend_upsells(
        self,
        policy: SpendingPolicy,
        cart_total: float,
        spend_state: Optional[UserSpendState] = None
    ) -> List[UpsellItem]:
        headroom = self.calculate_headroom(policy, cart_total, spend_state)
        available_room = headroom.effective_spendable_headroom

        recommendations: List[UpsellItem] = []
        for item in UPSELL_CATALOG:
            cat = item["category"].lower()
            # Category must be allowed
            if cat in policy.limits.category_caps and policy.limits.category_caps[cat] == 0:
                continue
            if policy.constraints.allowed_categories and cat not in [c.lower() for c in policy.constraints.allowed_categories]:
                continue

            fits = item["price"] <= available_room
            if fits:
                recommendations.append(UpsellItem(
                    id=item["id"],
                    title=item["title"],
                    price=item["price"],
                    category=item["category"],
                    merchant_margin_tier=item["merchant_margin_tier"],
                    fits_within_headroom=True,
                    projected_new_cart_total=cart_total + item["price"],
                    pitch=item["pitch"]
                ))

        # Sort recommendations by margin and price to maximize merchant revenue
        recommendations.sort(key=lambda x: (x.merchant_margin_tier == "HIGH", x.price), reverse=True)
        return recommendations
