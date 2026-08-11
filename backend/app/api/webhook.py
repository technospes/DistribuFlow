from fastapi import APIRouter, Request, HTTPException
import logging

from app.schemas.webhook import WebhookPayload
from app.agents.order_agent import build_agent_graph
from app.database.checkpointer import get_postgres_checkpointer
from langchain_core.messages import HumanMessage

router = APIRouter()
logger = logging.getLogger(__name__)

# Build the graph topology once
graph_builder = build_agent_graph()

@router.post("/whatsapp")
async def receive_whatsapp_webhook(request: Request, payload: WebhookPayload):
    """
    Receive messages from n8n/WhatsApp.
    Passes the message to the LangGraph agent for processing.
    """
    msg = payload.message
    logger.info(f"Received {msg.type} message from {msg.from_number}")
    
    if msg.type != "text" or not msg.text:
         return {"status": "ignored", "message": "Only text messages are supported currently."}

    try:
        # 1. Open the checkpointer connection
        async with get_postgres_checkpointer() as checkpointer:
            
            # 2. Compile the graph dynamically with the active checkpointer
            app = graph_builder.compile(checkpointer=checkpointer)
            
            # 3. Map the WhatsApp phone number to the LangGraph thread_id
            config = {
                "configurable": {
                    "thread_id": msg.from_number
                }
            }
            
            # 4. Setup the initial state payload. We only need to pass the new HumanMessage 
            # and the sender_phone. LangGraph's checkpointer will automatically pull the 
            # previous messages and append this new one to the list!
            state_input = {
                "messages": [HumanMessage(content=msg.text)],
                "sender_phone": msg.from_number
            }
            
            # 5. Invoke the graph (using ainvoke because we are async)
            result = await app.ainvoke(state_input, config=config)
            
            # 6. Extract the final AI response
            # Since our graph appends an AIMessage at the end, it will be the last element
            final_reply = result["messages"][-1].content
            
            return {
                "status": "success", 
                "intent_detected": result.get("intent"),
                "reply": final_reply
            }
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))