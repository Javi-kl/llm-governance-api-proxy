from pydantic import BaseModel, field_validator

from app.core.security import validate_pin


class UserCreate(BaseModel):
    username: str
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_password(cls, pin: str) -> str:

        return validate_pin(pin)


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}
