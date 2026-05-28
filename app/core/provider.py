"""Cliente HTTP al proveedor LLM externo (ADR-7).

Envía el prompt (ya procesado por el detector/policy) al LLM configurado
y devuelve la respuesta generada. Un único proveedor configurado por
variables de entorno — el cliente no elige proveedor en la petición.
"""

import httpx

from app.core.config import get_settings
from app.core.exceptions import ProviderError, ProviderTimeoutError


def enviar(prompt: str) -> str:
    """Envía el prompt al LLM y devuelve el texto generado."""
    settings = get_settings()
    body = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY.get_secret_value()}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            json=body,
            headers=headers,
            timeout=settings.LLM_PROVIDER_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        raise ProviderTimeoutError() from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else None
        raise ProviderError(status_code=status) from None
    except httpx.RequestError:
        raise ProviderError() from None
    except (KeyError, IndexError, TypeError):
        raise ProviderError() from None
