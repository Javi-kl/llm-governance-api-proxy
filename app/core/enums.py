import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class SensitiveCategory(str, enum.Enum):
    IDENTIFICACION = "identificacion"
    CONTACTO = "contacto"
    FINANCIERO = "financiero"


class PolicyAction(str, enum.Enum):
    """Orden de prioridad: BLOCK > MASK > ALLOW."""

    ALLOW = "allow"
    MASK = "mask"
    BLOCK = "block"
