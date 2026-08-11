import json
import logging
import difflib
from datetime import datetime, timedelta, timezone
from typing import TypedDict, Annotated, Sequence
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, add_messages

from app.config.config import settings
from app.database.session import SessionLocal
from app.database.models.distributor import Distributor
from app.database.models.order import Order
from app.database.models.auxiliary import SessionMemory
from app.services import order_service, catalog_service
from app.schemas.order import OrderCreate, OrderItemCreate, PaymentType

logger = logging.getLogger(__name__)

# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    sender_phone: str
    intent: str
    extracted_data: dict

# --- Initialize LLM ---
llm = ChatGroq(
    temperature=0, 
    model_name="llama3-8b-8192", 
    api_key=settings.GROQ_API_KEY
)

# --- 1. Deterministic Fuzzy Matching ---
def _fuzzy_match_product(raw_name: str, size: str, products: list):
    """
    Python-based deterministic matching.
    Calculates a confidence score (0.0 to 1.0) instead of relying on LLM hallucinations.
    """
    if not raw_name:
        return None, 0.0

    # Handle common phonetic / Hinglish typos
    aliases = {
        "nariyal": "coconut", "tel": "oil", "oyl": "oil", "coknut": "coconut", 
        "coconat": "coconut", "jasmin": "jasmine", "chameli": "jasmine",
        "amla": "amla", "thanda": "thanda", "navratna": "thanda"
    }
    
    search_term = str(raw_name).lower()
    for k, v in aliases.items():
        search_term = search_term.replace(k, v)
        
    if size:
        search_term += f" {size}"
        
    best_match = None
    best_score = 0.0
    
    for p in products:
        target = f"{p.product_name.lower()} {p.size_ml}ml" if p.size_ml else p.product_name.lower()
        
        # Calculate Levenshtein ratio
        score = difflib.SequenceMatcher(None, search_term, target).ratio()
        
        # Boost score if a complete word matches exactly (e.g., "coconut" is in "coconut oil")
        if any(word in target for word in search_term.split()):
            score += 0.15
            
        if score > best_score:
            best_score = score
            best_match = p
            
    return best_match, min(best_score, 1.0)


# --- 2. Core Agent Node ---
def process_message(state: AgentState):
    messages = state["messages"]
    sender_phone = state["sender_phone"]
    user_text = messages[-1].content
    
    db = SessionLocal()
    try:
        # Rule 1: Distributor Check
        distributor = db.query(Distributor).filter_by(phone_number=sender_phone).first()
        if not distributor or distributor.status != "active":
            return {"messages": [AIMessage(content="Sorry, your account is not active or not registered. Please contact the Sales Manager.")]}

        # Rule 5: Memory Retrieval
        memory = db.query(SessionMemory).filter_by(phone_number=sender_phone).first()
        if not memory:
            memory = SessionMemory(
                phone_number=sender_phone, 
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.add(memory)
            db.commit()

        # Check if memory expired
        if memory.expires_at < datetime.now(timezone.utc):
            memory.current_state = None
            memory.slots = {}
            memory.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.commit()

        # Prepare LLM Prompt (Catalog Injection & Intent Detection)
        system_prompt = f"""
        You are AI-DOMS, an order-taking assistant for B2B distributors in India.
        Extract the raw details from the user's message (Hindi/Hinglish/English).
        
        Categorize 'intent' as exactly one of: 
        "order" (wants to buy), "inquiry" (asking prices), "invoice_request" (wants bill/receipt), "confirmation" (saying yes/no), or "other".
        
        If intent is "confirmation", set "is_yes" to true or false.
        If intent is "order", extract the RAW product name they typed (do not guess SKUs).
        
        Return pure JSON:
        {{
            "intent": "order|inquiry|invoice_request|confirmation|other",
            "product_name": "raw text",
            "quantity_cartons": int,
            "size": "100ml or similar",
            "delivery_address": "address or DEFAULT",
            "requested_delivery_date": "date or ASAP",
            "is_yes": true/false/null
        }}
        """
        
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ])
        
        # Parse JSON safely
        try:
            raw_content = response.content.replace("```json", "").replace("```", "").strip()
            extracted = json.loads(raw_content)
        except json.JSONDecodeError:
            extracted = {"intent": "other"}

        intent = extracted.get("intent", "other")
        reply = "I didn't quite catch that. Could you please repeat?"

        # --- CONVERSATIONAL CONFIRMATION LOOP ---
        if memory.current_state == "pending_product_confirmation":
            is_yes = extracted.get("is_yes")
            # Fallback if LLM missed the intent
            if "yes" in user_text.lower() or "haan" in user_text.lower() or "ha" in user_text.lower():
                is_yes = True
            elif "no" in user_text.lower() or "nahi" in user_text.lower():
                is_yes = False
                
            if is_yes is True:
                # User confirmed! Move slots forward.
                memory.current_state = None
                extracted = memory.slots.get("raw_extracted", {})
                extracted["product_name"] = memory.slots.get("confirmed_sku_name") # Force exact match
                intent = "order" # Re-trigger the order flow
                db.commit()
            elif is_yes is False:
                memory.current_state = None
                memory.slots = {}
                db.commit()
                return {"messages": [AIMessage(content="Okay, order cancelled. What product would you like instead?")]}
            else:
                return {"messages": [AIMessage(content="Please reply with 'Yes' or 'No' to confirm the product.")]}

        # --- INTENT: INVOICE REQUEST ---
        if intent == "invoice_request":
            # Find the latest approved order for this distributor
            latest_order = db.query(Order).filter(
                Order.distributor_id == distributor.id,
                Order.status == "Approved"
            ).order_by(Order.created_at.desc()).first()
            
            if latest_order:
                reply = f"Your latest invoice for order {latest_order.order_number} is ready. It will be sent to you shortly."
            else:
                reply = "You don't have any recently approved orders with a generated invoice."
                
        # --- INTENT: INQUIRY ---
        elif intent == "inquiry":
            products = catalog_service.list_available_products(db)
            if not products:
                reply = "Our catalog is currently empty."
            else:
                prod_list = "\n".join([f"- {p.product_name} ({p.size_ml}ml): ₹{p.price_per_carton}/carton" for p in products])
                reply = f"Here is our current product catalog:\n{prod_list}"

        # --- INTENT: ORDER ---
        elif intent == "order":
            raw_name = extracted.get("product_name")
            size = extracted.get("size")
            qty = extracted.get("quantity_cartons")
            addr = extracted.get("delivery_address")
            date = extracted.get("requested_delivery_date")

            if raw_name and qty:
                # 1. Fetch real active catalog
                active_products = catalog_service.list_available_products(db)
                
                # 2. Python Deterministic Matching
                best_match, score = _fuzzy_match_product(raw_name, size, active_products)
                
                # 3. Confidence Routing (Rule 4)
                if score >= 0.75:
                    # HIGH CONFIDENCE -> Auto-Match
                    if not addr or not date:
                        reply = f"Got it ({best_match.product_name}). Please specify the delivery address and requested date."
                    else:
                        order_in = OrderCreate(
                            distributor_phone=sender_phone,
                            payment_type=PaymentType.CREDIT,
                            delivery_address=None if addr.upper() == "DEFAULT" else addr,
                            requested_delivery_date=date,
                            items=[OrderItemCreate(product_sku=best_match.sku, quantity_cartons=qty)]
                        )
                        try:
                            saved_order = order_service.process_draft_order(db, order_in)
                            reply = f"Successfully recorded! Order {saved_order.order_number} is now Draft (Total: ₹{saved_order.total_amount})."
                            # Clear slots on success
                            memory.slots = {}
                            db.commit()
                        except Exception as e:
                            reply = f"Order failed: {str(e)}"
                            
                elif 0.40 <= score < 0.75:
                    # MEDIUM CONFIDENCE -> Ask Confirmation
                    memory.current_state = "pending_product_confirmation"
                    memory.slots = {
                        "raw_extracted": extracted,
                        "confirmed_sku_name": best_match.product_name # Save what we suspect it is
                    }
                    db.commit()
                    reply = f"Did you mean {best_match.product_name} {best_match.size_ml}ml (Quantity: {qty})? Please reply Yes or No."
                    
                else:
                    # LOW CONFIDENCE -> Human Escalation
                    reply = f"I couldn't confidently find '{raw_name}' in our catalog. Let me escalate this to the Sales Manager."
            else:
                reply = "Please tell me the product name and how many cartons you need."

        return {"messages": [AIMessage(content=reply)]}

    except Exception as e:
        logger.error(f"Error in process_message: {e}")
        return {"messages": [AIMessage(content="An error occurred while processing your request.")]}
    finally:
        db.close()

# --- Graph Building ---
def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("process_message", process_message)
    workflow.set_entry_point("process_message")
    workflow.add_edge("process_message", END)
    return workflow