from pydantic import BaseModel, ConfigDict, field_validator,model_validator

from app.core import security


class UserCreate(BaseModel):
    username: str
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_password(cls, pin: str) -> str:

        return security.validate_pin(pin)


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, new_password: str) -> str:
        return security.validate_password_strength(new_password)
        
    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Las contraseñas no coinciden.")
        return self