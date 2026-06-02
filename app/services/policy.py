"""Política de gobernanza para prompts detectados.

Convierte categorías sensibles en una acción: allow, mask o block.
La prioridad es block > mask > allow.
También aplica el enmascarado de valores detectados.
"""

from app.core.enums import PolicyAction, SensitiveCategory
from app.services.detector import Detection

# ── Marcadores por tipo de patrón ──────────────────────────

_MARKERS: dict[str, str] = {
    "DNI": "[DNI/NIF]",
    "NIF": "[DNI/NIF]",
    "CIF": "[DNI/NIF]",
    "email": "[EMAIL]",
    "phone": "[TELEFONO]",
    "cp": "[CP]",
    "iban": "[IBAN]",
    "card": "[TARJETA]",
}

PRIVACY_SYSTEM_PROMPT = (
    "Los marcadores [DNI/NIF], [EMAIL], [TELEFONO] y [CP] representan datos "
    "personales reales que el usuario ha decidido compartir. Trátalos como "
    "si fueran los valores originales y no solicites al usuario que los "
    "proporcione o los modifique."
)

# ── Funciones públicas ─────────────────────────────────────


def evaluate(categories: list[SensitiveCategory]) -> PolicyAction:
    if not categories:
        return PolicyAction.ALLOW
    if SensitiveCategory.FINANCIAL in categories:
        return PolicyAction.BLOCK
    return PolicyAction.MASK


def mask_values(prompt: str, detections: list[Detection]) -> str:
    """Procesa de derecha a izquierda para que las posiciones de las
    detecciones anteriores no se desplacen al modificar el prompt.
    """
    result = prompt
    for d in sorted(detections, key=lambda d: d.start, reverse=True):
        marker = _MARKERS[d.pattern_name]
        result = result[: d.start] + marker + result[d.end :]
    return result
