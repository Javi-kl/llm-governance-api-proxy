from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str

    
class ChatResponse(BaseModel):
    request_id: str
    action: str                    # "allow" | "mask" | "block" | "error"
    provider_response: str | None  # None en block/error
    reason: str | None             # Solo en block/error
    detected_categories: list[str] # Solo en mask/block


class OpenAIRequest(BaseModel):
    model: str
    messages: list[dict]  # [{"role": "user", "content": "..."}]

    
class OpenAIResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list[dict]