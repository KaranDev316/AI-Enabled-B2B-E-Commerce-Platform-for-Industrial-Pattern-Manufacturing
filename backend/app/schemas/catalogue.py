from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class CategoryInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)


class CategoryResponse(CategoryInput):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProductInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    category_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=10000)
    material_type: str | None = Field(default=None, max_length=100)
    specifications: str | None = Field(default=None, max_length=10000)
    indicative_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    is_active: bool = True
