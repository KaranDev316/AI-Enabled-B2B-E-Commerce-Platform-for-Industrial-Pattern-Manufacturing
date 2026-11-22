from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class JobAssignmentInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    order_id: int = Field(gt=0)
    employee_id: int = Field(gt=0)
    instructions: str = Field(min_length=3,max_length=10000)

class JobUpdateInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_version: int = Field(ge=0, strict=True)
    action: Literal['progress','advance','pause','resume']
    progress: int = Field(ge=0,le=100,strict=True)
    note: str = Field(min_length=3,max_length=2000)
    customer_note: str | None = Field(default=None,max_length=500)
