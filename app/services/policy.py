"""Política de gobernanza — decide la acción para un conjunto de categorías
y aplica el enmascarado cuando la acción es MASK.

Mapeo (RF-3):
- IDENTIFICACION → MASK
- CONTACTO       → MASK
- FINANCIERO     → BLOCK

Prioridad: BLOCK > MASK > ALLOW (ADR-3).
"""

from app.core.enums import PolicyAction, SensitiveCategory
from app.services.detector import Detection

# ── Marcadores por tipo de patrón ──────────────────────────

_MARCADORES: dict[str, str] = {
    "DNI": "[DNI/NIF]",
    "NIF": "[DNI/NIF]",
    "CIF": "[DNI/NIF]",
    "email": "[EMAIL]",
    "telefono": "[TELEFONO]",
    "cp": "[CP]",
    "iban": "[IBAN]",
    "tarjeta": "[TARJETA]",
}


# ── Funciones públicas ─────────────────────────────────────

def evaluar(categorias: list[SensitiveCategory]) -> PolicyAction:
    if not categorias:
        return PolicyAction.ALLOW
    if SensitiveCategory.FINANCIERO in categorias:
        return PolicyAction.BLOCK
    return PolicyAction.MASK


def enmascarar(prompt: str, detections: list[Detection]) -> str:
    """Procesa de derecha a izquierda para que las posiciones de las
    detecciones anteriores no se desplacen al modificar el prompt.
    """
    resultado = prompt
    for d in sorted(detections, key=lambda d: d.start, reverse=True):
        marcador = _MARCADORES[d.pattern_name]
        resultado = resultado[:d.start] + marcador + resultado[d.end:]
    return resultado
