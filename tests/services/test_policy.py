from app.core.enums import PolicyAction, SensitiveCategory
from app.services.policy import evaluar


# ── Ciclo 1: Tracer bullet — vacío → ALLOW ────────────────

def test_given_no_categories_then_allow():
    assert evaluar([]) == PolicyAction.ALLOW


# ── Ciclo 2: Categorías MASK ──────────────────────────────


def test_given_identificacion_then_mask():
    assert evaluar([SensitiveCategory.IDENTIFICACION]) == PolicyAction.MASK


def test_given_contacto_then_mask():
    assert evaluar([SensitiveCategory.CONTACTO]) == PolicyAction.MASK


# ── Ciclo 3: Categoría BLOCK ──────────────────────────────


def test_given_financiero_then_block():
    assert evaluar([SensitiveCategory.FINANCIERO]) == PolicyAction.BLOCK


# ── Ciclo 4: Prioridad BLOCK > MASK > ALLOW ───────────────


def test_given_financiero_and_identificacion_then_block():
    assert evaluar(
        [SensitiveCategory.FINANCIERO, SensitiveCategory.IDENTIFICACION]
    ) == PolicyAction.BLOCK


def test_given_all_categories_then_block():
    assert evaluar([
        SensitiveCategory.IDENTIFICACION,
        SensitiveCategory.CONTACTO,
        SensitiveCategory.FINANCIERO,
    ]) == PolicyAction.BLOCK


# ── Ciclo 5: Múltiples MASK sin BLOCK ─────────────────────


def test_given_identificacion_and_contacto_then_mask():
    assert evaluar(
        [SensitiveCategory.IDENTIFICACION, SensitiveCategory.CONTACTO]
    ) == PolicyAction.MASK
