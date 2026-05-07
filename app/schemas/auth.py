from pydantic import BaseModel, field_validator
from app.core.security import validate_password_strength


class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:

        return validate_password_strength(password)

        
class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}

    