from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class IssueInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    job_id: int | None = Field(default=None, gt=0)
    issue_type: Literal['production','machine','material','drawing']
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    priority: Literal['high','medium','low']

class IssueHandlingInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_version: int = Field(strict=True, ge=0)
    status: Literal['open','in_review','in_progress','resolved']
    note: str = Field(min_length=3, max_length=2000)
