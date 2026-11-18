from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import RFQStatus, RFQType


class RFQFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    content_type: str
    file_size_bytes: int
    created_at: datetime
    can_preview: bool = False



class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    file_name: str
    url: str


class ProductSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    material_type: Optional[str] = None
    indicative_price: Optional[float] = None
    is_active: bool
    category_id: Optional[int] = None
    description: Optional[str] = None
    category_name: Optional[str] = None
    specifications: Optional[str] = None
    images: list[ProductImageResponse] = Field(default_factory=list)


class RFQCreateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str = Field(..., min_length=2, max_length=255)
    rfq_type: RFQType = RFQType.CUSTOM
    product_id: Optional[int] = None
    material: str = Field(..., min_length=2, max_length=100)
    quantity: int = Field(..., gt=0, description='Quantity must be greater than 0')
    description: Optional[str] = None
    dimensions: Optional[str] = Field(None, max_length=255)
    specifications: Optional[str] = None
    target_delivery_date: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

    @field_validator('title', 'material')
    @classmethod
    def strip_text(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError('Field cannot be empty or blank whitespace.')
        return clean


class RFQResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rfq_number: str
    customer_id: int
    rfq_type: str
    product_id: Optional[int] = None
    title: str
    material: str
    quantity: int
    description: Optional[str] = None
    dimensions: Optional[str] = None
    specifications: Optional[str] = None
    target_delivery_date: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    files: list[RFQFileOut] = Field(default_factory=list)


class RFQDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rfq_number: str
    customer_id: int
    rfq_type: str
    product_id: Optional[int] = None
    title: str
    material: str
    quantity: int
    description: Optional[str] = None
    dimensions: Optional[str] = None
    specifications: Optional[str] = None
    target_delivery_date: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    files: list[RFQFileOut] = Field(default_factory=list)

    # Context facts
    customer_email: str
    customer_company: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_phone: Optional[str] = None
    product_name: Optional[str] = None


class RFQStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: RFQStatus
