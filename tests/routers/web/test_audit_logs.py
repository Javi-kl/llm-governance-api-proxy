"""Tests de integración HTTP para la ruta web de logs de auditoría con filtros GET.

Verifican acceso, renderizado de metadatos sin contenido de prompts/respuestas,
y los filtros de búsqueda vía query string.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.services.audit import register_log
from tests.conftest import create_token

# ═══════════════════════════════════════════════════════════
# GET /dashboard/logs
# ═══════════════════════════════════════════════════════════


def test_given_no_cookie_then_audit_logs_returns_401(client: TestClient):
    """Sin cookie de sesión, el endpoint /dashboard/logs responde 401 (InvalidCredentialsError)."""
    response = client.get("/dashboard/logs", follow_redirects=False)

    assert response.status_code == 401


def test_given_regular_user_then_audit_logs_returns_403(
    client: TestClient, regular_user: User
):
    """Usuario con rol user autenticado → require_admin deniega el acceso con 403."""
    token = create_token(regular_user.id, regular_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard/logs", follow_redirects=False)

    assert response.status_code == 403


def test_given_admin_user_and_no_logs_then_audit_logs_shows_empty_state(
    client: TestClient, admin_user: User
):
    """Admin autenticado sin logs en BD → 200, HTML con título y mensaje de vacío."""
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard/logs", follow_redirects=False)

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    assert "Logs de auditoría" in response.text
    assert "No hay logs de auditoría registrados." in response.text


def test_given_admin_user_and_logs_then_audit_logs_renders_metadata(
    client: TestClient, admin_user: User, regular_user: User, db_session: Session
):
    """Admin autenticado con un log de auditoría → HTML con metadatos visibles,
    sin columnas de prompts ni respuestas."""
    # Crear un log de auditoría usando la función de servicio (no SQL directo)
    log = register_log(
        request_id="550e8400-e29b-41d4-a716-446655440000",
        user_id=regular_user.id,
        provider="openai",
        model="gpt-4o",
        action="block",
        detected_categories=["financiero"],
        latency_ms=450,
        status="success",
        db=db_session,
    )
    db_session.commit()

    # Acceder como admin
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get("/dashboard/logs", follow_redirects=False)

    # Contrato observable: HTTP 200 con HTML
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type

    html = response.text

    # Metadatos que DEBEN aparecer
    assert log.provider in html
    assert "Bloqueada" in html  # Etiqueta visible para action "block"
    assert "financiero" in html  # Categoría detectada

    # Contenido de prompts/respuestas NUNCA debe aparecer (RNF-3)
    assert "<th>Prompt</th>" not in html
    assert "<th>Respuesta</th>" not in html
    assert "provider_response" not in html


# ═══════════════════════════════════════════════════════════
# GET /dashboard/logs — filtros
# ═══════════════════════════════════════════════════════════


def test_given_empty_filter_fields_then_audit_logs_returns_html(
    client: TestClient, admin_user: User
):
    """Campos de filtro vacíos se normalizan sin error y devuelven la página HTML correcta."""
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get(
        "/dashboard/logs?action=&user_id=&date_from=&date_to=",
        follow_redirects=False,
    )

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
    assert "Logs de auditoría" in response.text
    assert "VALIDATION_ERROR" not in response.text


@pytest.mark.parametrize(
    "query_string, expected_message",
    [
        ("user_id=abc", "El usuario debe ser un número entero positivo."),
        ("date_from=fecha-mala", "La fecha desde tiene un formato inválido."),
        (
            "date_from=2026-06-13&date_to=2026-06-12",
            "La fecha desde no puede ser posterior a la fecha hasta.",
        ),
    ],
)
def test_given_invalid_filter_then_audit_logs_show_error_message(
    client: TestClient,
    admin_user: User,
    query_string: str,
    expected_message: str,
):
    """Filtros inválidos muestran mensaje de error en HTML sin código genérico VALIDATION_ERROR."""
    token = create_token(admin_user.id, admin_user.role)
    client.cookies.set("access_token", token)

    response = client.get(f"/dashboard/logs?{query_string}", follow_redirects=False)

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type

    html = response.text
    assert expected_message in html
    assert "VALIDATION_ERROR" not in html
