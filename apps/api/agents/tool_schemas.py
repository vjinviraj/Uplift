from pydantic import BaseModel, Field


class SearchCatalogInput(BaseModel):
    query: str = Field(min_length=1)
    category_hint: str | None = None


class SearchCatalogMatch(BaseModel):
    product_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price_paise: int = Field(ge=0)
    currency: str = Field(min_length=1)
    in_stock: bool


class SearchCatalogOutput(BaseModel):
    matches: list[SearchCatalogMatch] = Field(max_length=5)


class UpsellCandidate(BaseModel):
    product_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price_paise: int = Field(ge=0)
    reason_code: str = Field(min_length=1)
    max_autonomous: bool


class GetUpsellCandidatesInput(BaseModel):
    product_id: str = Field(min_length=1)


class GetUpsellCandidatesOutput(BaseModel):
    candidates: list[UpsellCandidate]


class PriceOrderLineItem(BaseModel):
    product_id: str = Field(min_length=1)
    qty: int = Field(gt=0)


class PriceOrderInput(BaseModel):
    line_items: list[PriceOrderLineItem] = Field(min_length=1)


class PriceOrderBreakdownItem(BaseModel):
    product_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    qty: int = Field(gt=0)
    unit_price_paise: int = Field(ge=0)
    line_total_paise: int = Field(ge=0)


class PriceOrderOutput(BaseModel):
    amount_paise: int = Field(ge=0)
    currency: str = Field(min_length=1)
    breakdown: list[PriceOrderBreakdownItem]