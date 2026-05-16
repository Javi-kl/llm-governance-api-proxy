from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core import security
from app.core.enums import UserRole


class UserCreate(BaseModel):
    username: str
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, pin: str) -> str:
        return security.validate_pin(pin)


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


