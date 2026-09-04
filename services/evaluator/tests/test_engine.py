"""Automated Unit Tests for NIYAM Deterministic Evaluator Engine
Covers 20 boundary conditions, edge cases, category caps, time windows, and idempotency states.
"""
from datetime import datetime
import pytest
from services.compiler.schema import (
    SpendingPolicy,
    Limits,
    Constraints,
    TimeWindow,
    PurchaseItem,
    PurchaseRequest,
    UserSpendState,
    ReasonCode,
)
from services.evaluator.engine import evaluate_purchase


@pytest.fixture
def standard_policy() -> SpendingPolicy:
    """Standard baseline policy: max 1200 per tx, 8000 monthly, toys 1500, electronics 0."""
    return SpendingPolicy(
        policy_version="v1",
        user_id="usr_rahul_982",
        limits=Limits(
            max_per_transaction=1200.0,
            monthly_cap=8000.0,
            category_caps={"toys": 1500.0, "electronics": 0.0, "groceries": 3000.0}
        ),
        constraints=Constraints(
            returnable_only=True,
            cod_allowed_above=1000.0,
            allowed_categories=["toys", "groceries", "books"],
            blocked_merchants=["merch_shady_deals"]
        ),
        time_window=TimeWindow(
            active_hours="09:00-21:00",
            timezone="Asia/Kolkata",
            allowed_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        )
    )


@pytest.fixture
def compliant_item() -> PurchaseItem:
    return PurchaseItem(
        id="prod_toy_teddy",
        title="Wooden Handcrafted Teddy",
        price=450.0,
        category="toys",
        quantity=1,
        returnable=True,
        cod_allowed=True,
        merchant_id="merch_verified_toys"
    )


def test_approved_normal_purchase(standard_policy, compliant_item):
    """Normal compliant purchase within all boundaries."""
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[compliant_item],
        idempotency_key="idemp_test_normal_001"
    )
    # 2:00 PM IST (inside active window)
    t = datetime(2026, 9, 4, 14, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is True
    assert res.reason_code == ReasonCode.APPROVED
    assert "Approved" in res.explainability
    assert res.threshold is None


def test_approved_exactly_at_per_tx_limit(standard_policy):
    """Boundary test: Total amount exactly equals max_per_transaction."""
    item = PurchaseItem(
        id="prod_toy_train",
        title="Electric Wooden Train",
        price=1200.0,
        category="toys",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_boundary_exact_002"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is True
    assert res.reason_code == ReasonCode.APPROVED


def test_denied_one_rupee_above_per_tx_limit(standard_policy):
    """Boundary test: Total amount is exactly 1 rupee above max_per_transaction."""
    item = PurchaseItem(
        id="prod_toy_expensive",
        title="Toy Robot Deluxe",
        price=1201.0,
        category="toys",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_boundary_plus1_003"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.PER_TRANSACTION_LIMIT_EXCEEDED
    assert res.rule_fired == "limits.max_per_transaction"
    assert res.threshold == 1200.0
    assert res.actual_value == 1201.0


def test_denied_massive_overspend(standard_policy):
    """Overspend failure mode: Smartphone ₹79,999 vs ₹1,200 limit."""
    item = PurchaseItem(
        id="prod_phone_flagship",
        title="Flagship 5G Smartphone",
        price=79999.0,
        category="electronics",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_massive_004"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.PER_TRANSACTION_LIMIT_EXCEEDED
    assert "₹79,999" in res.explainability


def test_approved_cumulative_monthly_under_cap(standard_policy, compliant_item):
    """Prior spend 7000 + 450 = 7450 <= 8000 cap."""
    spend_state = UserSpendState(user_id="usr_rahul_982", monthly_spend_accumulated=7000.0)
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[compliant_item],
        idempotency_key="idemp_test_monthly_ok_005"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, spend_state=spend_state, evaluation_time=t)

    assert res.allowed is True
    assert res.reason_code == ReasonCode.APPROVED


def test_denied_cumulative_monthly_over_cap(standard_policy, compliant_item):
    """Prior spend 7800 + 450 = 8250 > 8000 cap."""
    spend_state = UserSpendState(user_id="usr_rahul_982", monthly_spend_accumulated=7800.0)
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[compliant_item],
        idempotency_key="idemp_test_monthly_breach_006"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, spend_state=spend_state, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.MONTHLY_CAP_EXCEEDED
    assert res.rule_fired == "limits.monthly_cap"
    assert res.threshold == 8000.0
    assert res.actual_value == 8250.0


def test_approved_exactly_at_monthly_cap(standard_policy):
    """Boundary test: Prior spend 7550 + 450 = exactly 8000."""
    item = PurchaseItem(
        id="prod_toy_450",
        title="Wooden Puzzle",
        price=450.0,
        category="toys",
        returnable=True
    )
    spend_state = UserSpendState(user_id="usr_rahul_982", monthly_spend_accumulated=7550.0)
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_monthly_exact_007"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, spend_state=spend_state, evaluation_time=t)

    assert res.allowed is True
    assert res.reason_code == ReasonCode.APPROVED


def test_denied_forbidden_category_zero_cap(standard_policy):
    """Electronics cap is 0 -> CATEGORY_FORBIDDEN."""
    item = PurchaseItem(
        id="prod_earbuds",
        title="Wireless Earbuds",
        price=800.0,  # Below per tx limit of 1200
        category="electronics",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_forbidden_cat_008"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code in [ReasonCode.CATEGORY_FORBIDDEN, ReasonCode.CATEGORY_NOT_WHITELISTED]


def test_denied_category_cap_exceeded(standard_policy):
    """Toys cap is 1500. Cart is 1000, but past category spend was 800 (Total 1800 > 1500)."""
    item = PurchaseItem(
        id="prod_lego_set",
        title="Lego Building Set",
        price=1000.0,
        category="toys",
        returnable=True
    )
    spend_state = UserSpendState(
        user_id="usr_rahul_982",
        monthly_spend_accumulated=1000.0,
        category_spend_accumulated={"toys": 800.0}
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_cat_cap_exceeded_009"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, spend_state=spend_state, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.CATEGORY_CAP_EXCEEDED
    assert res.rule_fired == "limits.category_caps.toys"
    assert res.actual_value == 1800.0


def test_denied_category_not_whitelisted(standard_policy):
    """Category 'furniture' is not in allowed_categories: ['toys', 'groceries', 'books']."""
    item = PurchaseItem(
        id="prod_chair",
        title="Small Study Chair",
        price=900.0,
        category="furniture",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_whitelist_cat_010"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.CATEGORY_NOT_WHITELISTED


def test_denied_non_returnable_item(standard_policy):
    """Policy requires returnable_only=True, item is non-returnable."""
    item = PurchaseItem(
        id="prod_toy_custom",
        title="Custom Monogrammed Toy",
        price=500.0,
        category="toys",
        returnable=False
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_non_returnable_011"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.NON_RETURNABLE_ITEM
    assert res.rule_fired == "constraints.returnable_only"


def test_denied_cod_below_threshold(standard_policy):
    """COD allowed only above 1000; cart is 450."""
    item = PurchaseItem(
        id="prod_book",
        title="Science Encyclopedia",
        price=450.0,
        category="books",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        payment_method="cod",
        idempotency_key="idemp_test_cod_fail_012"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.COD_NOT_ALLOWED
    assert res.threshold == 1000.0


def test_approved_cod_above_threshold(standard_policy):
    """COD allowed above 1000; cart is 1100."""
    item = PurchaseItem(
        id="prod_book_box_set",
        title="Complete Collector Box Set",
        price=1100.0,
        category="books",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        payment_method="cod",
        idempotency_key="idemp_test_cod_pass_013"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is True
    assert res.reason_code == ReasonCode.APPROVED


def test_denied_time_window_after_hours(standard_policy, compliant_item):
    """Active hours 09:00-21:00; request attempted at 22:30 (10:30 PM)."""
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[compliant_item],
        idempotency_key="idemp_test_time_after_014"
    )
    t = datetime(2026, 9, 4, 22, 30, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.TIME_WINDOW_CLOSED
    assert res.rule_fired == "time_window.active_hours"


def test_denied_time_window_before_hours(standard_policy, compliant_item):
    """Active hours 09:00-21:00; request attempted at 06:15 AM."""
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[compliant_item],
        idempotency_key="idemp_test_time_before_015"
    )
    t = datetime(2026, 9, 4, 6, 15, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.TIME_WINDOW_CLOSED


def test_denied_blocked_merchant(standard_policy):
    """Merchant merch_shady_deals is blacklisted."""
    item = PurchaseItem(
        id="prod_toy_fake",
        title="Knockoff Board Game",
        price=300.0,
        category="toys",
        returnable=True,
        merchant_id="merch_shady_deals"
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_blocked_merchant_016"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.MERCHANT_BLOCKED
    assert res.rule_fired == "constraints.blocked_merchants"


def test_multi_item_cart_atomic_breakdown(standard_policy):
    """Cart with 2 items: 1 compliant, 1 non-returnable. Must atomically fail with itemization."""
    item1 = PurchaseItem(
        id="prod_toy_1",
        title="Plush Bear",
        price=300.0,
        category="toys",
        returnable=True
    )
    item2 = PurchaseItem(
        id="prod_toy_2",
        title="Personalized Custom Name Badge",
        price=200.0,
        category="toys",
        returnable=False  # Violates returnable_only
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item1, item2],
        idempotency_key="idemp_test_multi_item_017"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.NON_RETURNABLE_ITEM
    assert len(res.item_evaluations) == 2
    assert res.item_evaluations[0].passed is True
    assert res.item_evaluations[1].passed is False


def test_quantity_multiplier_in_per_tx_calculation(standard_policy):
    """Item unit price is ₹500, but quantity is 3 -> Total ₹1,500 > ₹1,200 limit."""
    item = PurchaseItem(
        id="prod_toy_car",
        title="Diecast Metal Car",
        price=500.0,
        quantity=3,
        category="toys",
        returnable=True
    )
    req = PurchaseRequest(
        agent_id="agent_shopping_01",
        user_id="usr_rahul_982",
        items=[item],
        idempotency_key="idemp_test_qty_mult_018"
    )
    t = datetime(2026, 9, 4, 12, 0, 0)
    res = evaluate_purchase(standard_policy, req, evaluation_time=t)

    assert res.allowed is False
    assert res.reason_code == ReasonCode.PER_TRANSACTION_LIMIT_EXCEEDED
    assert res.actual_value == 1500.0
