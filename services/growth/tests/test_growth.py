"""Unit Tests for NIYAM Growth & Revenue Optimization Engine
Validates headroom calculations, high-margin upsell recommendations,
and the 'Save the Sale' 1-Tap Policy Waiver conversion recovery lifecycle.
"""
import pytest
from services.compiler.schema import SpendingPolicy, Limits, Constraints, UserSpendState
from services.growth.engine import GrowthEngine, WaiverManager


@pytest.fixture
def test_policy() -> SpendingPolicy:
    return SpendingPolicy(
        policy_version="v1",
        user_id="usr_rahul_982",
        limits=Limits(
            max_per_transaction=1200.0,
            monthly_cap=8000.0,
            category_caps={"toys": 1500.0, "electronics": 0.0}
        ),
        constraints=Constraints(
            returnable_only=True,
            allowed_categories=["toys", "groceries", "books"]
        )
    )


def test_calculate_headroom(test_policy):
    """Cart is ₹450 against ₹1,200 per-tx limit -> Headroom should be ₹750."""
    growth = GrowthEngine()
    spend_state = UserSpendState(user_id="usr_rahul_982", monthly_spend_accumulated=2000.0)
    headroom = growth.calculate_headroom(test_policy, cart_total=450.0, spend_state=spend_state)

    assert headroom.per_tx_headroom == 750.0
    assert headroom.monthly_headroom == 5550.0  # 8000 - (2000 + 450)
    assert headroom.effective_spendable_headroom == 750.0
    assert headroom.fits_policy is True


def test_recommend_upsells(test_policy):
    """Headroom is ₹750 -> Recommends battery pack (₹250), gift wrap (₹120), bookmarks (₹150)."""
    growth = GrowthEngine()
    spend_state = UserSpendState(user_id="usr_rahul_982", monthly_spend_accumulated=1000.0)
    upsells = growth.recommend_upsells(test_policy, cart_total=450.0, spend_state=spend_state)

    assert len(upsells) > 0
    # Every recommendation must fit within available headroom
    for item in upsells:
        assert item.price <= 750.0
        assert item.category in ["toys", "groceries", "books"]


def test_waiver_lifecycle():
    """Validates request -> pending -> approve -> retrieve lifecycle."""
    mgr = WaiverManager(ttl_seconds=300)
    waiver = mgr.request_waiver(
        user_id="usr_rahul_982",
        agent_id="agent_shopper_01",
        cart_total=1350.0,
        policy_limit=1200.0,
        reason="Cart ₹1,350 exceeds ₹1,200 per-transaction cap."
    )

    assert waiver.status == "PENDING"
    assert waiver.delta_amount == 150.0

    # Approve
    approved = mgr.approve_waiver(waiver.waiver_id)
    assert approved is not None
    assert approved.status == "APPROVED"
    assert approved.approved_at is not None

    # Check
    retrieved = mgr.get_waiver(waiver.waiver_id)
    assert retrieved.status == "APPROVED"


def test_partial_fulfillment_split(test_policy):
    """Multi-item cart containing compliant toy (₹450) and forbidden earphone (₹899).
    Should isolate compliant item and offer partial fulfillment.
    """
    from services.compiler.schema import PurchaseItem
    growth = GrowthEngine()
    items = [
        PurchaseItem(id="item_toy", title="Teddy Bear", price=450.0, category="toys", returnable=True),
        PurchaseItem(id="item_phone", title="Earbuds", price=899.0, category="electronics", returnable=True)
    ]
    option = growth.analyze_partial_fulfillment(test_policy, items)
    assert option is not None
    assert option.can_fulfill_partial is True
    assert len(option.compliant_items) == 1
    assert option.compliant_items[0].id == "item_toy"
    assert len(option.breaching_items) == 1
    assert option.breaching_items[0]["id"] == "item_phone"
    assert option.compliant_subtotal == 450.0
    assert option.gated_amount == 899.0

