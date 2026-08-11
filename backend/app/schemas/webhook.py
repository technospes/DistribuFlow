from pydantic import BaseModel
from typing import Optional

# A simplified schema for the WhatsApp payload
class WhatsAppMessage(BaseModel):
    from_number: str
    text: Optional[str] = None
    audio_id: Optional[str] = None
    type: str # 'text' or 'audio'

class WebhookPayload(BaseModel):
    message: WhatsAppMessage