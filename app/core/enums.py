import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class SensitiveCategory(str, enum.Enum):
    IDENTIFICATION = "identificacion"
    CONTACT = "contacto"
    FINANCIAL = "financiero"


class PolicyAction(str, enum.Enum):
    """Orden de prioridad: BLOCK > MASK > ALLOW."""

    ALLOW = "allow"
    MASK = "mask"
    BLOCK = "block"


class MessageRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
