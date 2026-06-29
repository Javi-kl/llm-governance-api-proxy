from pydantic import BaseModel, field_validator, model_validator
from app.core import security


class LoginRequest(BaseModel):
    username: str
    credential: str


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


class UserPinResetRequest(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_new_pin(cls, pin: str) -> str:
        return security.validate_pin(pin)
