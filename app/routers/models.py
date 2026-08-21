from typing import Annotated
import time
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, status

from app.db.models.user import User
from app.schemas.models import ModelInfo, ModelListResponse
from app.dependencies.api_key_auth_dep import api_key_auth_dep
from app.core.config import get_settings
from app.core import exceptions


router = APIRouter(prefix="/models", tags=["openai"])


MODEL_CREATED_AT = int(time.time())


def _build_model_info() -> ModelInfo:
    return ModelInfo(
        id=get_settings().LLM_MODEL,
        created=MODEL_CREATED_AT,
        owned_by=urlparse(str(get_settings().LLM_BASE_URL)).hostname or "unknown",
    )


@router.get(
    "",
    response_model=ModelListResponse,
    status_code=status.HTTP_200_OK,
)
def get_models(_: Annotated[User, Depends(api_key_auth_dep)]) -> ModelListResponse:

    model_data = _build_model_info()

    return ModelListResponse(data=[model_data])


@router.get("/{model_id}", response_model=ModelInfo)
def get_model_id(
    model_id: str, _: Annotated[User, Depends(api_key_auth_dep)]
) -> ModelInfo:
    if model_id != get_settings().LLM_MODEL:
        raise exceptions.ModelNotFoundError(model_id)

    return _build_model_info()
