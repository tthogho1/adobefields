from pydantic import BaseModel, Field, computed_field
from typing import Optional


class AgreementSummary(BaseModel):
    id: str
    name: str
    status: Optional[str] = None


class AgreementDetail(BaseModel):
    id: str
    name: str
    status: str


class AgreementFilterResult(BaseModel):
    in_progress: list[AgreementDetail] = Field(default_factory=list)
    canceled: list[AgreementDetail] = Field(default_factory=list)
    expired: list[AgreementDetail] = Field(default_factory=list)
    other: list[AgreementDetail] = Field(default_factory=list)

    @computed_field
    @property
    def in_progress_count(self) -> int:
        return len(self.in_progress)

    @computed_field
    @property
    def canceled_count(self) -> int:
        return len(self.canceled)

    @computed_field
    @property
    def expired_count(self) -> int:
        return len(self.expired)

    @computed_field
    @property
    def other_count(self) -> int:
        return len(self.other)
