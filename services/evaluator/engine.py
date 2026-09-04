"""NIYAM Deterministic Policy Evaluator
Pure mathematical function: (policy, request, spend_state) -> EvaluationResult.
Never makes network calls, never calls LLMs, operates in sub-millisecond runtime.
"""
from datetime import datetime, time, timezone
from typing import Optional, Dict
import zoneinfo
from services.compiler.schema import (
    SpendingPolicy,
    PurchaseRequest,
    UserSpendState,
    EvaluationResult,
    ReasonCode,
    ItemEvaluation,
)


def evaluate_purchase(
    policy: SpendingPolicy,
    request: PurchaseRequest,
    spend_state: Optional[UserSpendState] = None,
    evaluation_time: Optional[datetime] = None,
) -> EvaluationResult:
    """Pure deterministic policy evaluation.
    
    Evaluates in strict mathematical order:
    1. Time Window & Active Hours
    2. Merchant Blacklist
    3. Maximum Per-Transaction Limit
    4. Cumulative Monthly Budget Cap
    5. Category Forbidden / Cap Checks
    6. Category Whitelist Checks
    7. Returnability Constraints
    8. Payment Method / COD Constraints
    
    Returns an explainable EvaluationResult with exact rule fired and thresholds.
    """
    total_amount = request.total_amount if request.total_amount is not None else request.get_calculated_total()
    if spend_state is None:
        spend_state = UserSpendState(user_id=request.user_id)

    # 1. Time Window Check
    if policy.time_window and policy.time_window.active_hours:
        check_time = evaluation_time or request.request_timestamp or datetime.now(timezone.utc)
        tz_name = policy.time_window.timezone or "Asia/Kolkata"
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            local_time = check_time.astimezone(tz)
        except Exception:
            local_time = check_time

        # Day of week check
        day_str = local_time.strftime("%a")
        if policy.time_window.allowed_days and day_str not in policy.time_window.allowed_days:
            return EvaluationResult(
                allowed=False,
                reason_code=ReasonCode.TIME_WINDOW_CLOSED,
                rule_fired="time_window.allowed_days",
                threshold=policy.time_window.allowed_days,
                actual_value=day_str,
                explainability=f"Blocked: Purchases not allowed on {day_str}. Allowed days: {', '.join(policy.time_window.allowed_days)}."
            )

        # Hours check: "HH:MM-HH:MM"
        try:
            start_str, end_str = policy.time_window.active_hours.split("-")
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
            start_time = time(sh, sm)
            end_time = time(eh, em)
            curr_time = local_time.time()

            is_open = False
            if start_time <= end_time:
                is_open = start_time <= curr_time <= end_time
            else:
                # Spans midnight e.g. 22:00-04:00
                is_open = curr_time >= start_time or curr_time <= end_time

            if not is_open:
                return EvaluationResult(
                    allowed=False,
                    reason_code=ReasonCode.TIME_WINDOW_CLOSED,
                    rule_fired="time_window.active_hours",
                    threshold=policy.time_window.active_hours,
                    actual_value=curr_time.strftime("%H:%M"),
                    explainability=f"Blocked: Current time {curr_time.strftime('%H:%M')} IST is outside active purchasing window ({policy.time_window.active_hours})."
                )
        except Exception:
            pass

    # 2. Blocked Merchants Check
    if policy.constraints.blocked_merchants:
        for item in request.items:
            if item.merchant_id and item.merchant_id in policy.constraints.blocked_merchants:
                return EvaluationResult(
                    allowed=False,
                    reason_code=ReasonCode.MERCHANT_BLOCKED,
                    rule_fired="constraints.blocked_merchants",
                    threshold=policy.constraints.blocked_merchants,
                    actual_value=item.merchant_id,
                    explainability=f"Blocked: Merchant '{item.merchant_id}' is explicitly blacklisted by policy."
                )

    # 3. Maximum Per-Transaction Limit Check
    if total_amount > policy.limits.max_per_transaction:
        delta = total_amount - policy.limits.max_per_transaction
        return EvaluationResult(
            allowed=False,
            reason_code=ReasonCode.PER_TRANSACTION_LIMIT_EXCEEDED,
            rule_fired="limits.max_per_transaction",
            threshold=policy.limits.max_per_transaction,
            actual_value=total_amount,
            explainability=f"Blocked: Total cart amount ₹{total_amount:,.2f} exceeds per-transaction limit of ₹{policy.limits.max_per_transaction:,.2f} (Over budget by ₹{delta:,.2f})."
        )

    # 4. Cumulative Monthly Spend Cap Check
    projected_monthly_spend = spend_state.monthly_spend_accumulated + total_amount
    if projected_monthly_spend > policy.limits.monthly_cap:
        remaining = max(0.0, policy.limits.monthly_cap - spend_state.monthly_spend_accumulated)
        return EvaluationResult(
            allowed=False,
            reason_code=ReasonCode.MONTHLY_CAP_EXCEEDED,
            rule_fired="limits.monthly_cap",
            threshold=policy.limits.monthly_cap,
            actual_value=projected_monthly_spend,
            explainability=f"Blocked: Cumulative monthly spend would reach ₹{projected_monthly_spend:,.2f}, exceeding monthly cap of ₹{policy.limits.monthly_cap:,.2f} (Remaining allowance: ₹{remaining:,.2f})."
        )

    # 5. Itemized Breakdown: Category Caps & Whitelists & Returnability
    item_evaluations = []
    category_totals: Dict[str, float] = {}
    for item in request.items:
        cat = item.category.lower().strip()
        item_cost = item.price * item.quantity
        category_totals[cat] = category_totals.get(cat, 0.0) + item_cost

        # Category Whitelist Check
        if policy.constraints.allowed_categories and cat not in [c.lower() for c in policy.constraints.allowed_categories]:
            item_evaluations.append(ItemEvaluation(
                product_id=item.id,
                category=item.category,
                price=item.price,
                passed=False,
                reason=f"Category '{item.category}' is not in allowed categories whitelist"
            ))
            return EvaluationResult(
                allowed=False,
                reason_code=ReasonCode.CATEGORY_NOT_WHITELISTED,
                rule_fired="constraints.allowed_categories",
                threshold=policy.constraints.allowed_categories,
                actual_value=item.category,
                explainability=f"Blocked: Category '{item.category}' for item '{item.title}' is not permitted by user policy.",
                item_evaluations=item_evaluations
            )

        # Forbidden Category (Cap == 0)
        cat_cap = policy.limits.category_caps.get(cat)
        if cat_cap is not None and cat_cap == 0:
            item_evaluations.append(ItemEvaluation(
                product_id=item.id,
                category=item.category,
                price=item.price,
                passed=False,
                reason=f"Category '{item.category}' is strictly forbidden (cap = 0)"
            ))
            return EvaluationResult(
                allowed=False,
                reason_code=ReasonCode.CATEGORY_FORBIDDEN,
                rule_fired=f"limits.category_caps.{cat}",
                threshold=0,
                actual_value=item.price,
                explainability=f"Blocked: Category '{item.category}' is strictly forbidden by policy (limit is ₹0). Item '{item.title}' cannot be purchased.",
                item_evaluations=item_evaluations
            )

        # Returnable Constraint Check
        if policy.constraints.returnable_only and not item.returnable:
            item_evaluations.append(ItemEvaluation(
                product_id=item.id,
                category=item.category,
                price=item.price,
                passed=False,
                reason="Item is non-returnable"
            ))
            return EvaluationResult(
                allowed=False,
                reason_code=ReasonCode.NON_RETURNABLE_ITEM,
                rule_fired="constraints.returnable_only",
                threshold=True,
                actual_value=False,
                explainability=f"Blocked: Item '{item.title}' is non-returnable. Policy strictly requires returnable goods only.",
                item_evaluations=item_evaluations
            )

        item_evaluations.append(ItemEvaluation(
            product_id=item.id,
            category=item.category,
            price=item.price,
            passed=True,
            reason="Item compliant with item-level constraints"
        ))

    # 6. Aggregate Category Spend Cap Check
    for cat, cart_cat_spend in category_totals.items():
        cat_cap = policy.limits.category_caps.get(cat)
        if cat_cap is not None and cat_cap > 0:
            past_cat_spend = spend_state.category_spend_accumulated.get(cat, 0.0)
            projected_cat_spend = past_cat_spend + cart_cat_spend
            if projected_cat_spend > cat_cap:
                delta = projected_cat_spend - cat_cap
                return EvaluationResult(
                    allowed=False,
                    reason_code=ReasonCode.CATEGORY_CAP_EXCEEDED,
                    rule_fired=f"limits.category_caps.{cat}",
                    threshold=cat_cap,
                    actual_value=projected_cat_spend,
                    explainability=f"Blocked: Total spend for category '{cat}' would reach ₹{projected_cat_spend:,.2f}, exceeding category cap of ₹{cat_cap:,.2f} (Over cap by ₹{delta:,.2f}).",
                    item_evaluations=item_evaluations
                )

    # 7. Cash On Delivery (COD) Constraints Check
    if request.payment_method.lower() == "cod":
        if policy.constraints.cod_allowed_above is not None and total_amount < policy.constraints.cod_allowed_above:
            return EvaluationResult(
                allowed=False,
                reason_code=ReasonCode.COD_NOT_ALLOWED,
                rule_fired="constraints.cod_allowed_above",
                threshold=policy.constraints.cod_allowed_above,
                actual_value=total_amount,
                explainability=f"Blocked: COD is only permitted for orders above ₹{policy.constraints.cod_allowed_above:,.2f}. Current cart is ₹{total_amount:,.2f}.",
                item_evaluations=item_evaluations
            )

    # All checks passed!
    return EvaluationResult(
        allowed=True,
        reason_code=ReasonCode.APPROVED,
        rule_fired=None,
        threshold=None,
        actual_value=total_amount,
        explainability=f"Approved: Cart total ₹{total_amount:,.2f} complies with per-transaction limit (₹{policy.limits.max_per_transaction:,.2f}), monthly cap (₹{policy.limits.monthly_cap:,.2f}), and all category constraints.",
        item_evaluations=item_evaluations
    )
