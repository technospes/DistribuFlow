from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import logging
import os
import tempfile
from groq import AsyncGroq

from langchain_core.messages import HumanMessage
from app.agents.order_agent import build_agent_graph
from app.database.checkpointer import get_postgres_checkpointer
from app.config.config import settings
from fastapi.responses import FileResponse
from app.database.session import SessionLocal
from app.database.models import Invoice
from uuid import UUID

router = APIRouter()
logger = logging.getLogger(__name__)

# 1. Build the graph topology once globally
graph_builder = build_agent_graph()

# 2. Initialize the Groq Async Client for Whisper Transcription
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

class ChatRequest(BaseModel):
    phone_number: str
    message: str

async def process_with_agent(phone_number: str, user_text: str) -> str:
    """Helper function to run the LangGraph agent for both text and voice inputs."""
    async with get_postgres_checkpointer() as checkpointer:
        # Compile the graph dynamically with the active checkpointer
        app = graph_builder.compile(checkpointer=checkpointer)
        
        # Map the WhatsApp phone number to the LangGraph thread_id
        config = {
            "configurable": {
                "thread_id": phone_number
            }
        }
        
        # Setup the initial state payload
        state_input = {
            "messages": [HumanMessage(content=user_text)],
            "sender_phone": phone_number
        }
        
        # Invoke the graph
        result = await app.ainvoke(state_input, config=config)
        
        # Extract and return the final AI response
        return result["messages"][-1].content


@router.get("/download-invoice/{invoice_id}")
async def download_invoice(invoice_id: UUID, phone_number: str):
    """Endpoint for n8n to download the physical PDF file securely."""
    from app.database.models import Order, Distributor # Needed for secure joins
    db = SessionLocal()
    try:
        # IDOR Security Check: Ensure the invoice belongs to the requesting phone number
        invoice = (
            db.query(Invoice)
            .join(Order)
            .join(Distributor)
            .filter(Invoice.id == invoice_id)
            .filter(Distributor.phone_number == phone_number)
            .first()
        )
        
        if not invoice or not os.path.exists(invoice.file_path):
            raise HTTPException(status_code=404, detail="Invoice PDF not found or unauthorized access.")
        
        return FileResponse(
            path=invoice.file_path, 
            filename=f"{invoice.invoice_number}.pdf", 
            media_type="application/pdf"
        )
    finally:
        db.close()


@router.post("/")
async def chat_with_agent(request: ChatRequest):
    """Endpoint for processing standard text messages."""
    try:
        final_reply = await process_with_agent(request.phone_number, request.message)
        
        return {
            "status": "success",
            "reply": final_reply
        }
            
    except Exception as e:
        logger.error(f"Error processing text chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/")
async def handle_voice_message(
    phone_number: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """Endpoint for processing voice notes downloaded from Meta via n8n."""
    temp_audio_path = None
    try:
        # 1. Save the incoming binary audio stream to a temporary file
        # Meta typically sends voice notes in .ogg format
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(await audio_file.read())
            temp_audio_path = temp_audio.name
            
        logger.info(f"Saved temporary audio file for {phone_number} at {temp_audio_path}")
        
        # 2. Transcribe the audio using Groq's Whisper API
        with open(temp_audio_path, "rb") as file:
            transcription = await groq_client.audio.transcriptions.create(
                file=("audio.ogg", file.read()),
                model="whisper-large-v3",
                response_format="text",
                language="hi" # Setting to 'hi' optimizes for Hindi and Hinglish
            )
            
        logger.info(f"Transcription for {phone_number}: {transcription}")
        
        # 3. Pass the transcribed text into your existing LangGraph logic
        final_reply = await process_with_agent(phone_number, transcription)
        
        return {
            "status": "success",
            "transcription_debug": transcription, # Useful for debugging in n8n
            "reply": final_reply
        }
        
    except Exception as e:
        logger.error(f"Error processing voice chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 4. Clean up the temporary file so we don't leak disk space
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)