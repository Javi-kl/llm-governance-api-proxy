from app.core.enums import PolicyAction, SensitiveCategory
from app.services.detector import Detection
from app.services.policy import mask_values, evaluate


# ── Ciclo 1: Tracer bullet — vacío → ALLOW ────────────────


def test_given_no_categories_then_allow():
    assert evaluate([]) == PolicyAction.ALLOW


def test_given_identification_then_mask():
    assert evaluate([SensitiveCategory.IDENTIFICATION]) == PolicyAction.MASK


def test_given_contact_then_mask():
    assert evaluate([SensitiveCategory.CONTACT]) == PolicyAction.MASK


# ── Ciclo 3: Categoría BLOCK ──────────────────────────────


def test_given_financial_then_block():
    assert evaluate([SensitiveCategory.FINANCIAL]) == PolicyAction.BLOCK


def test_given_financial_and_identification_then_block():
    assert (
        evaluate([SensitiveCategory.FINANCIAL, SensitiveCategory.IDENTIFICATION])
        == PolicyAction.BLOCK
    )


def test_given_all_categories_then_block():
    assert (
        evaluate(
            [
                SensitiveCategory.IDENTIFICATION,
                SensitiveCategory.CONTACT,
                SensitiveCategory.FINANCIAL,
            ]
        )
        == PolicyAction.BLOCK
    )


# ── Ciclo 5: Múltiples MASK sin BLOCK ─────────────────────


def test_given_identification_and_contact_then_mask():
    assert (
        evaluate([SensitiveCategory.IDENTIFICATION, SensitiveCategory.CONTACT])
        == PolicyAction.MASK
    )


# ── Enmascarado ───────────────────────────────────────────


def test_given_no_detections_then_returns_unchanged():
    assert mask_values("hola", []) == "hola"


def test_given_one_email_then_masks_it():
    detections = [
        Detection(SensitiveCategory.CONTACT, "email", "j@x.com", 6, 14),
    ]
    assert mask_values("email j@x.com", detections) == "email [EMAIL]"


def test_given_dni_and_phone_then_masks_both():
    detections = [
        Detection(SensitiveCategory.IDENTIFICATION, "DNI", "12345678Z", 0, 9),
        Detection(SensitiveCategory.CONTACT, "phone", "612345678", 12, 21),
    ]
    result = mask_values("12345678Z y 612345678", detections)
    assert result == "[DNI/NIF] y [TELEFONO]"


def test_given_two_emails_then_masks_both():
    detections = [
        Detection(SensitiveCategory.CONTACT, "email", "a@b.com", 0, 7),
        Detection(SensitiveCategory.CONTACT, "email", "c@d.es", 10, 16),
    ]
    result = mask_values("a@b.com o c@d.es", detections)
    assert result == "[EMAIL] o [EMAIL]"


def test_given_right_to_left_order_then_positions_stay_valid():
    # Si no se procesa de derecha a izquierda, el segundo reemplazo fallaría
    detections = [
        Detection(SensitiveCategory.CONTACT, "cp", "CP 28001", 0, 8),
        Detection(SensitiveCategory.IDENTIFICATION, "DNI", "12345678Z", 10, 19),
    ]
    result = mask_values("CP 28001, 12345678Z", detections)
    assert result == "[CP], [DNI/NIF]"
