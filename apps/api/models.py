from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    category: str
    price_paise: int
    currency: str = "INR"
    in_stock: bool = True
    description: str


class CompatibilityMap(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    product_id: str
    upsell_product_id: str
    reason_code: str
    max_autonomous: bool = False


class BuyerProfile(SQLModel, table=True):
    id: str = Field(primary_key=True)
    objective: str
    max_budget_paise: int
    category_hint: str | None = None
    platform: str | None = None
    franchise: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Session(SQLModel, table=True):
    id: str = Field(primary_key=True)
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: str
    buyer_profile_id: str
    customer_ref: str


class PurchaseSessionState(SQLModel, table=True):
    id: str = Field(primary_key=True)
    request_json: str
    offer_json: str
    status: str = "AWAITING_APPROVAL"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )



class ExperimentObservation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    scenario_id: str | None = Field(default=None, index=True)
    arm: str = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class CartLineItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str
    product_id: str
    qty: int
    is_upsell: bool = False


class PolicyConfig(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    version: str
    max_single_item_price_paise: int
    max_order_total_without_extra_confirm_paise: int
    max_upsells_per_session: int = 1
    allowed_product_ids: str | None = None
    effective_from: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AuditEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    agent_run_id: str
    session_id: str
    actor_type: str
    action_id: str
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    decision: str | None = None
    reason: str | None = None
    policy_version: str | None = None
    buyer_budget_paise: int | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None
    payload_json: str

class Order(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str
    amount_paise: int
    currency: str = "INR"
    status: str
    razorpay_order_id: str | None = None
    idempotency_key: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Payment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    order_id: int
    razorpay_payment_id: str
    status: str
    method: str
    verified_at: datetime | None = None
    failure_reason: str | None = None

class PurchaseApproval(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str
    approved: bool
    amount_paise: int
    policy_version: str
    offer_hash: str
    extra_confirmation: bool = False
    confirmed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )