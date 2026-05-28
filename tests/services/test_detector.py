from app.core.enums import SensitiveCategory
from app.services.detector import Detection, analizar


# ── Ciclo 0: Tracer bullet — prompt vacío ────────────────

def test_given_empty_prompt_then_no_detections():
    assert analizar("") == []


def test_given_whitespace_then_no_detections():
    assert analizar("   \n\t  ") == []


def test_given_clean_text_then_no_detections():
    assert analizar("La capital de Francia es París.") == []


# ── Ciclo 1: DNI ────────────────────────────────────────


def test_given_valid_dni_then_detects():
    detections = analizar("Mi DNI es 12345678Z")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.IDENTIFICACION,
        pattern_name="DNI",
        match="12345678Z",
        start=10,
        end=19,
    )


def test_given_dni_in_mid_text_then_detects():
    detections = analizar("Titular: 12345678Z, fecha: ayer")

    assert len(detections) == 1
    assert detections[0].match == "12345678Z"
    assert detections[0].start == 9
    assert detections[0].end == 18


def test_given_dni_with_invalid_letter_then_no_detection():
    # I no pertenece al conjunto de letras DNI válidas
    assert analizar("DNI 12345678I") == []


def test_given_eight_digits_without_letter_then_no_detection():
    assert analizar("Número 12345678 solo") == []


# ── Ciclo 2: Email ───────────────────────────────────────


def test_given_valid_email_then_detects():
    detections = analizar("Mi email es javier@example.com")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.CONTACTO,
        pattern_name="email",
        match="javier@example.com",
        start=12,
        end=30,
    )


def test_given_email_with_subdomain_then_detects():
    detections = analizar("Contacto: user@mail.example.org")

    assert len(detections) == 1
    assert detections[0].match == "user@mail.example.org"


def test_given_email_without_tld_then_no_detection():
    # Sin TLD (.com, .es...) no es un email válido
    assert analizar("admin@localhost") == []


# ── Ciclo 3: DNI + email juntos (verificación) ────────────


def test_given_dni_and_email_then_both_detected():
    detections = analizar("DNI 12345678Z, email j@x.com")

    assert len(detections) == 2
    categories = {d.category for d in detections}
    assert categories == {SensitiveCategory.IDENTIFICACION, SensitiveCategory.CONTACTO}


def test_given_two_emails_then_both_detected():
    detections = analizar("a@b.com y c@d.es")

    assert len(detections) == 2
    assert all(d.category == SensitiveCategory.CONTACTO for d in detections)
    assert detections[0].match == "a@b.com"
    assert detections[1].match == "c@d.es"


# ── Ciclo 4: Teléfono ────────────────────────────────────


def test_given_spanish_mobile_then_detects_contacto():
    detections = analizar("Llámame al 612345678")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.CONTACTO,
        pattern_name="telefono",
        match="612345678",
        start=11,
        end=20,
    )


def test_given_nine_digits_not_spanish_phone_then_no_detection():
    # No empieza por 6-9, no es teléfono español
    assert analizar("Código: 512345678") == []


def test_given_seven_digits_then_no_detection():
    # Demasiado corto para ser teléfono
    assert analizar("Número 1234567") == []


# ── Ciclo 5: Teléfono excluido por contexto ───────────────


def test_given_phone_preceded_by_order_then_no_detection():
    # "nº" indica número de pedido, no teléfono personal
    assert analizar("pedido nº 612345678") == []


def test_given_phone_preceded_by_invoice_then_no_detection():
    assert analizar("factura: 612345678") == []


def test_given_phone_preceded_by_reference_then_no_detection():
    assert analizar("ref. 612345678") == []


def test_given_phone_with_personal_context_then_detects():
    # "número" no está en la lista de exclusión — contexto personal
    detections = analizar("Mi número es 612345678")

    assert len(detections) == 1
    assert detections[0].pattern_name == "telefono"


# ── Ciclo 6: IBAN ────────────────────────────────────────


def test_given_valid_spanish_iban_then_detects_financiero():
    detections = analizar("Cuenta ES9121000418450200051332")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.FINANCIERO,
        pattern_name="iban",
        match="ES9121000418450200051332",
        start=7,
        end=31,
    )


def test_given_iban_with_spaces_then_detects():
    # El validador sanitiza espacios antes de MOD 97
    detections = analizar("ES91 2100 0418 4502 0005 1332")

    assert len(detections) == 1
    assert detections[0].pattern_name == "iban"


def test_given_fake_iban_then_no_detection():
    # MOD 97 falla — no es un IBAN real
    assert analizar("ES0012345678901234567890") == []


# ── Ciclo 7: Tarjeta de crédito ────────────────────────────


def test_given_valid_credit_card_then_detects_financiero():
    detections = analizar("Pago con 4111111111111111")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.FINANCIERO,
        pattern_name="tarjeta",
        match="4111111111111111",
        start=9,
        end=25,
    )


def test_given_credit_card_with_spaces_then_detects():
    # Luhn se aplica tras sanitizar espacios
    detections = analizar("4111 1111 1111 1111")

    assert len(detections) == 1
    assert detections[0].pattern_name == "tarjeta"


def test_given_credit_card_with_dashes_then_detects():
    detections = analizar("4111-1111-1111-1111")

    assert len(detections) == 1
    assert detections[0].pattern_name == "tarjeta"


def test_given_16_digits_failing_luhn_then_no_detection():
    # Formato correcto (16 dígitos) pero Luhn falla
    assert analizar("Número 1234567890123456") == []


def test_given_15_digits_then_no_card_detection():
    # Demasiado corto, el regex exige 16 dígitos exactos
    assert analizar("123456789012345") == []


# ── Ciclo 8: CP con prefijo explícito ──────────────────────


def test_given_cp_with_prefix_then_detects():
    detections = analizar("CP 28001 Madrid")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.CONTACTO,
        pattern_name="cp",
        match="CP 28001",
        start=0,
        end=8,
    )


def test_given_cp_with_codigo_postal_then_detects():
    detections = analizar("código postal: 08001 Barcelona")

    assert len(detections) == 1
    assert detections[0].pattern_name == "cp"


def test_given_5_digit_amount_then_no_detection():
    # Sin prefijo CP, no se detecta — contrato de seguridad
    assert analizar("total: 23456 euros") == []


def test_given_5_digit_invoice_then_no_detection():
    assert analizar("factura nº 28001") == []


def test_given_5_digits_in_text_then_no_detection():
    assert analizar("Madrid 28001 capital") == []


# ── Ciclo 9: NIF + CIF ───────────────────────────────────


def test_given_valid_nie_then_detects():
    detections = analizar("NIE: X1234567L")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.IDENTIFICACION,
        pattern_name="NIF",
        match="X1234567L",
        start=5,
        end=14,
    )


def test_given_nie_with_invalid_letter_then_no_detection():
    # I no pertenece al conjunto de letras válidas
    assert analizar("NIE: X1234567I") == []


def test_given_valid_cif_then_detects():
    detections = analizar("CIF: B12345678")

    assert len(detections) == 1
    assert detections[0] == Detection(
        category=SensitiveCategory.IDENTIFICACION,
        pattern_name="CIF",
        match="B12345678",
        start=5,
        end=14,
    )


def test_given_cif_with_invalid_first_letter_then_no_detection():
    # I no es letra CIF válida
    assert analizar("I12345678") == []


# ── Ciclo 10: Smoke test + edge cases ─────────────────────


def test_given_prompt_with_all_categories_then_all_detected():
    detections = analizar(
        "DNI 12345678Z, email j@x.com, cuenta ES9121000418450200051332"
    )

    categories = {d.category for d in detections}
    assert categories == {
        SensitiveCategory.IDENTIFICACION,
        SensitiveCategory.CONTACTO,
        SensitiveCategory.FINANCIERO,
    }
    assert len(detections) >= 3


def test_given_match_at_text_start_then_detects():
    # Sin texto previo para comprobar exclusión contextual
    detections = analizar("612345678 llámame")

    assert len(detections) == 1
    assert detections[0].pattern_name == "telefono"


def test_given_match_at_text_end_then_detects():
    detections = analizar("Mi número 612345678")

    assert len(detections) == 1
    assert detections[0].pattern_name == "telefono"


def test_given_iban_does_not_trigger_other_patterns():
    # Un IBAN español no debe detectarse también como tarjeta o DNI
    detections = analizar("ES9121000418450200051332")

    assert len(detections) == 1
    assert detections[0].pattern_name == "iban"
