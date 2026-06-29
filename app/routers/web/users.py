"""Rutas web de gestión de usuarios del panel de administración."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import exceptions
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth_dep import require_admin
from app.routers.web.common import _render_template
from app.schemas.auth import UserPinResetRequest
from app.schemas.user import UserCreate
from app.services import admin

router = APIRouter()


def _form_value_to_str(value: object) -> str:
    """Normaliza campos de formulario; ignora uploads u otros tipos inesperados."""
    return value if isinstance(value, str) else ""


def _render_users_panel(
    request: Request,
    db: Session,
    *,
    message: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    """Renderiza el fragmento HTMX con la tabla y los mensajes visibles."""
    result = admin.list_users(db)
    return _render_template(
        request,
        "users_panel.html",
        users=result.items,
        total=result.total,
        message=message,
        error=error,
    )


@router.get("/dashboard/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Muestra la gestión de usuarios normales del panel admin."""
    result = admin.list_users(db)
    return _render_template(
        request,
        "users.html",
        user=current_user,
        users=result.items,
        total=result.total,
        message=None,
        error=None,
    )


@router.post("/dashboard/users", response_class=HTMLResponse)
async def create_user(
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Crea un usuario normal desde formulario HTMX y repinta el panel."""
    form = await request.form()
    username = _form_value_to_str(form.get("username")).strip()
    pin = _form_value_to_str(form.get("pin"))

    try:
        admin.register(UserCreate(username=username, pin=pin), db)
    except ValidationError:
        return _render_users_panel(
            request,
            db,
            error=(
                "El username debe tener entre 4 y 19 caracteres "
                "y el PIN entre 5 y 6 dígitos."
            ),
        )
    except exceptions.UserAlreadyExistsError:
        return _render_users_panel(
            request,
            db,
            error="Este username ya está registrado.",
        )

    return _render_users_panel(
        request,
        db,
        message="Usuario creado correctamente.",
    )


@router.post("/dashboard/users/{user_id}/deactivate", response_class=HTMLResponse)
async def deactivate_user(
    user_id: int,
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Desactiva un usuario normal y repinta el panel."""
    try:
        admin.deactivate_user(user_id, db)
    except exceptions.UserNotFoundError:
        return _render_users_panel(request, db, error="Usuario no encontrado.")
    except exceptions.CannotModifyAdminError:
        return _render_users_panel(
            request,
            db,
            error="Los administradores no se gestionan desde este panel.",
        )
    except exceptions.InactiveUserError:
        return _render_users_panel(request, db, error="El usuario ya está inactivo.")

    return _render_users_panel(request, db, message="Usuario desactivado.")


@router.post("/dashboard/users/{user_id}/pin", response_class=HTMLResponse)
async def reset_user_pin(
    user_id: int,
    request: Request,
    current_user: Annotated[User, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Resetea el PIN de un usuario normal y repinta el panel."""
    form = await request.form()
    pin = _form_value_to_str(form.get("pin"))

    try:
        admin.reset_user_pin(user_id, UserPinResetRequest(pin=pin), db)
    except ValidationError:
        return _render_users_panel(
            request,
            db,
            error="El PIN debe contener entre 5 y 6 dígitos.",
        )
    except exceptions.UserNotFoundError:
        return _render_users_panel(request, db, error="Usuario no encontrado.")
    except exceptions.CannotModifyAdminError:
        return _render_users_panel(
            request,
            db,
            error="Los administradores no se gestionan desde este panel.",
        )
    except exceptions.InactiveUserError:
        return _render_users_panel(
            request,
            db,
            error="No se puede resetear el PIN de un usuario inactivo.",
        )

    return _render_users_panel(request, db, message="PIN actualizado.")
