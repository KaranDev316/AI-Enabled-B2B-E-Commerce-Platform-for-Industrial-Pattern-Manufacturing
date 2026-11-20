from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class QuoteItemInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    description: str = Field(min_length=1, max_length=500)
    quantity: int = Field(gt=0, le=100000)
    unit_price: Decimal = Field(ge=0, le=Decimal('999999999.99'), max_digits=11, decimal_places=2)


class QuoteDraftInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    items: list[QuoteItemInput] = Field(default_factory=list, max_length=50)
    tax_percent: Decimal = Field(default=Decimal('0'), ge=0, le=100, max_digits=5, decimal_places=2)
    lead_time_days: int | None = Field(default=None, gt=0, le=3650)
    valid_until: AwareDatetime | None = None
    notes: str = Field(default='', max_length=4000)


class QuoteCreateInput(QuoteDraftInput):
    # Optimistic check supplements the RFQ row lock, including first-version races.
    expected_version: int = Field(ge=0)


class QuoteUpdateInput(QuoteDraftInput):
    expected_revision: int = Field(ge=1)


class QuoteSendInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=1)


class QuoteDecisionInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: Literal['reject', 'request_changes']
    message: str = Field(min_length=1, max_length=4000)
