"""Política de gobernanza — decide la acción para un conjunto de categorías.

Mapeo (RF-3):
- IDENTIFICACION → MASK
- CONTACTO       → MASK
- FINANCIERO     → BLOCK

Prioridad: BLOCK > MASK > ALLOW (ADR-3).
"""

from app.core.enums import PolicyAction, SensitiveCategory


def evaluar(categorias: list[SensitiveCategory]) -> PolicyAction:
    if not categorias:
        return PolicyAction.ALLOW
    if SensitiveCategory.FINANCIERO in categorias:
        return PolicyAction.BLOCK
    return PolicyAction.MASK
