from app.core.enums import PolicyAction, SensitiveCategory
from app.services.detector import Detection
from app.services.policy import enmascarar, evaluar


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


# ── Enmascarado ───────────────────────────────────────────


def test_given_no_detections_then_returns_unchanged():
    assert enmascarar("hola", []) == "hola"


def test_given_one_email_then_masks_it():
    detections = [
        Detection(SensitiveCategory.CONTACTO, "email", "j@x.com", 6, 14),
    ]
    assert enmascarar("email j@x.com", detections) == "email [EMAIL]"


def test_given_dni_and_phone_then_masks_both():
    detections = [
        Detection(SensitiveCategory.IDENTIFICACION, "DNI", "12345678Z", 0, 9),
        Detection(SensitiveCategory.CONTACTO, "telefono", "612345678", 12, 21),
    ]
    resultado = enmascarar("12345678Z y 612345678", detections)
    assert resultado == "[DNI/NIF] y [TELEFONO]"


def test_given_two_emails_then_masks_both():
    detections = [
        Detection(SensitiveCategory.CONTACTO, "email", "a@b.com", 0, 7),
        Detection(SensitiveCategory.CONTACTO, "email", "c@d.es", 10, 16),
    ]
    resultado = enmascarar("a@b.com o c@d.es", detections)
    assert resultado == "[EMAIL] o [EMAIL]"


def test_given_right_to_left_order_then_positions_stay_valid():
    # Si no se procesa de derecha a izquierda, el segundo reemplazo fallaría
    detections = [
        Detection(SensitiveCategory.CONTACTO, "cp", "CP 28001", 0, 8),
        Detection(SensitiveCategory.IDENTIFICACION, "DNI", "12345678Z", 10, 19),
    ]
    resultado = enmascarar("CP 28001, 12345678Z", detections)
    assert resultado == "[CP], [DNI/NIF]"
