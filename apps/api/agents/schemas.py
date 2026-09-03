from pydantic import BaseModel, Field


class PurchaseRequest(BaseModel):
    query: str = Field(min_length=1)
    budget_paise: int | None = Field(default=None, ge=0)
    category_hint: str | None = None
    platform_hint: str | None = None
    franchise_hint: str | None = None


class UpsellProposal(BaseModel):
    product_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class MerchantAgentProposal(BaseModel):
    product_id: str = Field(min_length=1)
    upsell: UpsellProposal | None = None


class PurchaseOfferBreakdownItem(BaseModel):
    product_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    qty: int = Field(gt=0)
    unit_price_paise: int = Field(ge=0)
    line_total_paise: int = Field(ge=0)


class PurchaseOffer(BaseModel):
    product_id: str = Field(min_length=1)
    upsell_product_id: str | None = None
    upsell_reason: str | None = None
    amount_paise: int = Field(ge=0)
    currency: str = Field(min_length=1)
    breakdown: list[PurchaseOfferBreakdownItem] = Field(min_length=1)
    policy_decision: str = Field(min_length=1)
    policy_reason: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)

class PurchaseConfirmation(BaseModel):
    approved: bool
    amount_paise: int = Field(ge=0)