"""Detector de datos sensibles mediante regex + validación algorítmica.

Catálogo MVP (8 patrones, 3 categorías):
| Patrón   | Categoría       | Regex | Validación | Exc. contexto         |
|----------|-----------------|-------|-----------|-----------------------|
| DNI      | IDENTIFICACION  | Sí    | — (Fase 2)| —                     |
| NIF      | IDENTIFICACION  | Sí    | — (Fase 2)| —                     |
| CIF      | IDENTIFICACION  | Sí    | — (Fase 2)| —                     |
| email    | CONTACTO        | Sí    | —         | —                     |
| teléfono | CONTACTO        | Sí    | —         | pedido, factura...    |
| cp       | CONTACTO        | Sí    | —         | — (prefijo en regex)  |
| iban     | FINANCIERO      | Sí    | MOD 97    | —                     |
| tarjeta  | FINANCIERO      | Sí    | Luhn      | —                     |
"""

import re
from dataclasses import dataclass
from typing import Callable

from app.core.enums import SensitiveCategory


@dataclass
class Detection:
    """Un dato sensible detectado en el prompt."""

    category: SensitiveCategory
    pattern_name: str
    match: str
    start: int
    end: int


@dataclass
class _Patron:
    """Patrón de detección interno."""

    name: str
    category: SensitiveCategory
    regex: str
    validator: Callable[[str], bool] | None = None
    negative_prefixes: list[str] | None = None


# ── Patrones de detección ───────────────────────────────────

_DNI_REGEX = r"(?<!\d)\d{8}[A-HJ-NP-TV-Z](?!\d)"
_EMAIL_REGEX = r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b"
_TELEFONO_REGEX = r"(?<!\d)[6-9]\d{8}(?!\d)"
_TELEFONO_EXCLUIR = [
    "pedido",
    "factura",
    "ref",
    "albarán",
    "id",
    "nº",
    "expediente",
    "caso",
    "incidencia",
    "ticket",
]
_IBAN_REGEX = r"\b[A-Z]{2}\d{2}(?:[\s-]?[A-Z0-9]){11,30}\b"
_TARJETA_REGEX = r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
_CP_REGEX = (
    r"\b(?:CP|código\s+postal|cód\.\s*postal|codigo\s+postal)"
    r"\s*[:#.-]?\s*\d{5}\b"
)
_NIF_REGEX = r"(?<!\d)[XYZ]\d{7}[A-HJ-NP-TV-Z](?!\d)"
_CIF_REGEX = r"\b[A-HJ-NP-SUVW]\d{7}[A-Z0-9]\b"


# ── Helpers internos ───────────────────────────────────────


def _es_contexto_negativo(texto: str, match_start: int, prefixes: list[str]) -> bool:
    """Comprueba si el match está precedido por alguna palabra de exclusión."""
    preceding = texto[:match_start].lower()
    if not preceding:
        return False
    for prefix in prefixes:
        patron = rf"(?:^|\s){re.escape(prefix.lower())}[\s:.#-]*$"
        if re.search(patron, preceding):
            return True
    return False


def _validar_iban(valor: str) -> bool:
    """Valida un IBAN mediante el algoritmo MOD 97."""
    iban = re.sub(r"[\s-]", "", valor).upper()
    if len(iban) < 15:
        return False
    reordenado = iban[4:] + iban[:4]
    digitos = ""
    for c in reordenado:
        if c.isalpha():
            digitos += str(ord(c) - 55)
        else:
            digitos += c
    return int(digitos) % 97 == 1


def _validar_luhn(valor: str) -> bool:
    """Valida un número de tarjeta mediante el algoritmo de Luhn (MOD 10)."""
    digitos = re.sub(r"[\s-]", "", valor)
    if not digitos.isdigit() or len(digitos) < 13:
        return False
    total = 0
    for i, char in enumerate(reversed(digitos)):
        d = int(char)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ── Lista de patrones ──────────────────────────────────────

_PATRONES: list[_Patron] = [
    _Patron("DNI", SensitiveCategory.IDENTIFICACION, _DNI_REGEX),
    _Patron("NIF", SensitiveCategory.IDENTIFICACION, _NIF_REGEX),
    _Patron("CIF", SensitiveCategory.IDENTIFICACION, _CIF_REGEX),
    _Patron("email", SensitiveCategory.CONTACTO, _EMAIL_REGEX),
    _Patron(
        "telefono",
        SensitiveCategory.CONTACTO,
        _TELEFONO_REGEX,
        negative_prefixes=_TELEFONO_EXCLUIR,
    ),
    _Patron(
        "iban",
        SensitiveCategory.FINANCIERO,
        _IBAN_REGEX,
        validator=_validar_iban,
    ),
    _Patron(
        "tarjeta",
        SensitiveCategory.FINANCIERO,
        _TARJETA_REGEX,
        validator=_validar_luhn,
    ),
    _Patron("cp", SensitiveCategory.CONTACTO, _CP_REGEX),
]


# ── Función pública ────────────────────────────────────────


def analizar(prompt: str) -> list[Detection]:
    """Escanea el prompt en busca de datos sensibles."""
    detections: list[Detection] = []

    for patron in _PATRONES:
        for match in re.finditer(patron.regex, prompt):
            if patron.negative_prefixes and _es_contexto_negativo(
                prompt, match.start(), patron.negative_prefixes
            ):
                continue
            if patron.validator and not patron.validator(match.group()):
                continue
            detections.append(
                Detection(
                    category=patron.category,
                    pattern_name=patron.name,
                    match=match.group(),
                    start=match.start(),
                    end=match.end(),
                )
            )

    return detections
