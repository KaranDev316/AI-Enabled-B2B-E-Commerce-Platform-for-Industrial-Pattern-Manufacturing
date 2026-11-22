from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Quantity = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=3)]
Unit = Literal['kg', 'g', 'litre', 'metre', 'piece']

class MaterialInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    code: str = Field(min_length=2, max_length=40, pattern=r'^[A-Z0-9][A-Z0-9_-]*$')
    name: str = Field(min_length=2, max_length=150)
    category: Literal['Raw Material', 'Consumable', 'Tool'] = 'Raw Material'
    unit: Unit
    minimum_stock: Quantity = Decimal('0')
    location: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=5000)

    @field_validator('code', mode='before')
    @classmethod
    def normalise_code(cls, value):
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode='after')
    def whole_piece_threshold(self):
        if self.unit == 'piece' and self.minimum_stock != self.minimum_stock.to_integral_value():
            raise ValueError('Piece quantities must be whole numbers.')
        return self

class MaterialResponse(MaterialInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    quantity: Decimal
    stock_status: str
    created_at: datetime
    updated_at: datetime

class AdjustmentInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    direction: Literal['addition', 'deduction']
    amount: Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
    reason: str = Field(min_length=3, max_length=1000)

class AdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    request_id: str
    material_id: int
    material_code: str
    unit: str
    direction: str
    amount: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    reason: str
    actor_email: str
    created_at: datetime
