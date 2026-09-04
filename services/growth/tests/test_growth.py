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


def test_whatsapp_notifier_token_lifecycle():
    """Validates cryptographic HMAC token generation and verification."""
    from services.growth.whatsapp import WhatsAppNotifier
    notifier = WhatsAppNotifier()
    waiver_id = "wv_test_998877"
    expires_at = 1757000000.0

    token = notifier.generate_waiver_token(waiver_id, expires_at)
    assert isinstance(token, str)
    assert len(token) == 24

    # Valid verification
    assert notifier.verify_waiver_token(waiver_id, expires_at, token) is True

    # Tampered token
    assert notifier.verify_waiver_token(waiver_id, expires_at, "invalid_token_123456789") is False

    # Tampered waiver ID or expiry
    assert notifier.verify_waiver_token("wv_different", expires_at, token) is False
    assert notifier.verify_waiver_token(waiver_id, expires_at + 100, token) is False


def test_whatsapp_notifier_dispatch_simulated():
    """Validates simulated WhatsApp dispatch and message structure."""
    from services.growth.whatsapp import WhatsAppNotifier
    from services.growth.engine import PolicyWaiver
    import time

    notifier = WhatsAppNotifier(public_base_url="https://niyam.onrender.com")
    waiver = PolicyWaiver(
        waiver_id="wv_demo_123",
        user_id="usr_rahul_982",
        agent_id="agent_shopper_01",
        cart_total=2499.0,
        policy_limit=1500.0,
        delta_amount=999.0,
        reason="Exceeds ₹1,500 limit",
        status="PENDING",
        created_at=time.time(),
        expires_at=time.time() + 900
    )

    alert = notifier.dispatch_waiver_alert(waiver, item_title="Mechanical Keyboard")

    assert alert["waiver_id"] == "wv_demo_123"
    assert alert["mode"] == "simulated"
    assert alert["dispatched"] is True
    assert "https://niyam.onrender.com/waivers/wv_demo_123/approve?token=" in alert["approve_url"]
    assert "Mechanical Keyboard" in alert["message_preview"]
    assert "₹2,499.00" in alert["message_preview"]
    assert "₹999.00" in alert["message_preview"]


def test_whatsapp_notifier_twilio_fallback():
    """Validates graceful degradation if Twilio API credentials fail or network errors out."""
    from services.growth.whatsapp import WhatsAppNotifier
    from services.growth.engine import PolicyWaiver
    import time

    # Provide dummy credentials that will fail HTTP post
    notifier = WhatsAppNotifier(
        account_sid="AC_dummy_sid_00000",
        auth_token="dummy_auth_token_00000",
        from_whatsapp="whatsapp:+14155238886"
    )
    assert notifier.is_live_configured() is True

    waiver = PolicyWaiver(
        waiver_id="wv_fallback_test",
        user_id="usr_rahul_982",
        agent_id="agent_shopper_01",
        cart_total=1800.0,
        policy_limit=1200.0,
        delta_amount=600.0,
        reason="Testing fallback",
        status="PENDING",
        created_at=time.time(),
        expires_at=time.time() + 900
    )

    # Must NOT raise exception; must fall back to simulated_fallback
    alert = notifier.dispatch_waiver_alert(waiver, item_title="Noise Cancelling Headphones")
    assert alert["mode"] == "simulated_fallback"
    assert "fallback_reason" in alert
    assert alert["dispatched"] is True


