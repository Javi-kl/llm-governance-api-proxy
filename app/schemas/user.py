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

    @field_validator("username")
    @classmethod
    def validate_username(cls, username: str) -> str:
        if not 3 < len(username) < 20:
            raise ValueError("Username debe tener entre 3 y 20 caracteres")
        return username


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
