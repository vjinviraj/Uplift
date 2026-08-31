from apps.api.models import PolicyConfig
from apps.api.policy.engine import check_policy


def test_order_at_max_total_is_allowed():
    policy = PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    result = check_policy(
        policy=policy,
        total_paise=500_000,
        buyer_budget_paise=500_000,
        upsell_count=0,
    )

    assert result.decision == "ALLOWED"

def test_order_above_buyer_budget_is_rejected():
    policy = PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    result = check_policy(
        policy=policy,
        total_paise=300_000,
        buyer_budget_paise=250_000,
        upsell_count=0,
    )

    assert result.decision == "REJECTED"

def test_second_upsell_is_rejected():
    policy = PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    result = check_policy(
        policy=policy,
        total_paise=300_000,
        buyer_budget_paise=500_000,
        upsell_count=2,
    )

    assert result.decision == "REJECTED"

def test_upsell_above_autonomous_price_limit_requires_confirmation():
    policy = PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    result = check_policy(
        policy=policy,
        total_paise=300_000,
        buyer_budget_paise=500_000,
        upsell_count=1,
        upsell_price_paise=150_000,
    )

    assert result.decision == "REQUIRES_CONFIRMATION"

def test_order_above_autonomous_total_requires_confirmation():
    policy = PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    result = check_policy(
        policy=policy,
        total_paise=500_001,
        buyer_budget_paise=600_000,
        upsell_count=0,
    )

    assert result.decision == "REQUIRES_CONFIRMATION"

def test_product_not_in_allowed_list_is_rejected():
    policy = PolicyConfig(
        version="v1",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids="GAME-001,GAME-002",
    )

    result = check_policy(
        policy=policy,
        total_paise=300_000,
        buyer_budget_paise=500_000,
        upsell_count=0,
        product_ids=["GAME-003"],
    )

    assert result.decision == "REJECTED"

def test_policy_result_contains_policy_version():
    policy = PolicyConfig(
        version="v2",
        max_single_item_price_paise=100_000,
        max_order_total_without_extra_confirm_paise=500_000,
        max_upsells_per_session=1,
        allowed_product_ids=None,
    )

    result = check_policy(
        policy=policy,
        total_paise=300_000,
        buyer_budget_paise=500_000,
        upsell_count=0,
    )

    assert result.policy_version == "v2"