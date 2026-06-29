"""Detección de datos sensibles en prompts.

Escanea texto con patrones regex y validadores específicos.
Agrupa detecciones por categoría de riesgo para que policy.py decida
si permitir, enmascarar o bloquear la solicitud.
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
class _Pattern:
    """Patrón de detección interno."""

    name: str
    category: SensitiveCategory
    regex: str
    validator: Callable[[str], bool] | None = None
    negative_prefixes: list[str] | None = None


# ── Patrones de detección ───────────────────────────────────

_DNI_REGEX = r"(?<!\d)\d{8}[A-HJ-NP-TV-Z](?!\d)"
_EMAIL_REGEX = r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b"
_PHONE_REGEX = r"(?<!\d)[6-9]\d{8}(?!\d)"
_PHONE_EXCLUSIONS = [
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
_CARD_REGEX = r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"
_CP_REGEX = (
    r"\b(?:CP|código\s+postal|cód\.\s*postal|codigo\s+postal)"
    r"\s*[:#.-]?\s*\d{5}\b"
)
_NIF_REGEX = r"(?<!\d)[XYZ]\d{7}[A-HJ-NP-TV-Z](?!\d)"
_CIF_REGEX = r"\b[A-HJ-NP-SUVW]\d{7}[A-Z0-9]\b"


# ── Helpers internos ───────────────────────────────────────


def _is_negative_context(text: str, match_start: int, prefixes: list[str]) -> bool:
    preceding = text[:match_start].lower()
    if not preceding:
        return False
    for prefix in prefixes:
        pattern = rf"(?:^|\s){re.escape(prefix.lower())}[\s:.#-]*$"
        if re.search(pattern, preceding):
            return True
    return False


def _validate_iban(value: str) -> bool:
    """Valida un IBAN mediante el algoritmo MOD 97."""
    iban = re.sub(r"[\s-]", "", value).upper()
    if len(iban) < 15:
        return False
    rearranged = iban[4:] + iban[:4]
    digits = ""
    for c in rearranged:
        if c.isalpha():
            digits += str(ord(c) - 55)
        else:
            digits += c
    return int(digits) % 97 == 1


def _validate_luhn(value: str) -> bool:
    """Valida un número de tarjeta mediante el algoritmo de Luhn (MOD 10)."""
    digits = re.sub(r"[\s-]", "", value)
    if not digits.isdigit() or len(digits) < 13:
        return False
    total = 0
    for i, char in enumerate(reversed(digits)):
        d = int(char)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ── Lista de patrones ──────────────────────────────────────

_PATTERNS: list[_Pattern] = [
    _Pattern("DNI", SensitiveCategory.IDENTIFICATION, _DNI_REGEX),
    _Pattern("NIF", SensitiveCategory.IDENTIFICATION, _NIF_REGEX),
    _Pattern("CIF", SensitiveCategory.IDENTIFICATION, _CIF_REGEX),
    _Pattern("email", SensitiveCategory.CONTACT, _EMAIL_REGEX),
    _Pattern(
        "phone",
        SensitiveCategory.CONTACT,
        _PHONE_REGEX,
        negative_prefixes=_PHONE_EXCLUSIONS,
    ),
    _Pattern(
        "iban",
        SensitiveCategory.FINANCIAL,
        _IBAN_REGEX,
        validator=_validate_iban,
    ),
    _Pattern(
        "card",
        SensitiveCategory.FINANCIAL,
        _CARD_REGEX,
        validator=_validate_luhn,
    ),
    _Pattern("cp", SensitiveCategory.CONTACT, _CP_REGEX),
]


# ── Función pública ────────────────────────────────────────


def analyze(prompt: str) -> list[Detection]:
    detections: list[Detection] = []

    for pattern in _PATTERNS:
        for match in re.finditer(pattern.regex, prompt):
            if pattern.negative_prefixes and _is_negative_context(
                prompt, match.start(), pattern.negative_prefixes
            ):
                continue
            if pattern.validator and not pattern.validator(match.group()):
                continue
            detections.append(
                Detection(
                    category=pattern.category,
                    pattern_name=pattern.name,
                    match=match.group(),
                    start=match.start(),
                    end=match.end(),
                )
            )

    return detections
