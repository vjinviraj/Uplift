from dataclasses import dataclass

from apps.api.models import PolicyConfig


@dataclass(frozen=True)
class PolicyResult:
    decision: str
    reason: str
    policy_version: str

def check_policy(
    *,
    policy: PolicyConfig,
    total_paise: int,
    buyer_budget_paise: int,
    upsell_count: int,
    upsell_price_paise: int = 0,
    product_ids: list[str] | None = None,
) -> PolicyResult:
    if total_paise > buyer_budget_paise:
        return PolicyResult(
            decision="REJECTED",
            reason="Order total exceeds the buyer's maximum budget.",
            policy_version=policy.version,
        )

    if upsell_count > policy.max_upsells_per_session:
        return PolicyResult(
            decision="REJECTED",
            reason="Maximum upsells per session has been exceeded.",
            policy_version=policy.version,
        )

    if policy.allowed_product_ids is not None and product_ids is not None:
        allowed_ids = {
            product_id.strip()
            for product_id in policy.allowed_product_ids.split(",")
            if product_id.strip()
        }

        if any(product_id not in allowed_ids for product_id in product_ids):
            return PolicyResult(
                decision="REJECTED",
                reason="One or more products are not allowed by merchant policy.",
                policy_version=policy.version,
            )

    if (
        upsell_count > 0
        and upsell_price_paise > policy.max_single_item_price_paise
    ):
        return PolicyResult(
            decision="REQUIRES_CONFIRMATION",
            reason="Upsell price exceeds the autonomous upsell limit.",
            policy_version=policy.version,
        )

    if total_paise <= policy.max_order_total_without_extra_confirm_paise:
        return PolicyResult(
            decision="ALLOWED",
            reason="Order total is within the merchant's autonomous limit.",
            policy_version=policy.version,
        )

    return PolicyResult(
        decision="REQUIRES_CONFIRMATION",
        reason="Order total exceeds the autonomous merchant limit.",
        policy_version=policy.version,
    )