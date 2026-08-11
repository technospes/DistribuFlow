import json
import logging
import difflib
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import TypedDict, Annotated, Sequence, Optional, Literal

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.config.config import settings
from app.database.session import SessionLocal
from app.database.models.distributor import Distributor
from app.database.models.order import Order
from app.database.models.auxiliary import SessionMemory, Invoice
from app.services import order_service, catalog_service
from app.schemas.order import OrderCreate, OrderItemCreate, PaymentType

logger = logging.getLogger(__name__)

# --- 1. State & Schemas ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    sender_phone: str
    intent: str
    extracted_data: dict


class OrderExtraction(BaseModel):
    product_name: Optional[str] = Field(default=None, description="Raw product name mentioned by the user.")
    size: Optional[str] = Field(default=None, description="Size or volume, e.g. 100ml, 500ml.")
    quantity_cartons: Optional[int] = Field(default=None, description="Number of cartons requested.")
    payment_type: Optional[str] = Field(default=None, description="Must be exactly 'credit', 'cod', or 'prepaid'.")
    delivery_address: Optional[str] = Field(default=None, description="Delivery address. If 'same' or 'default', return DEFAULT.")
    requested_delivery_date: Optional[str] = Field(default=None, description="Requested delivery date/day.")
    is_yes: Optional[bool] = Field(default=None, description="If answering a Yes/No question, true or false.")


class IntentAndExtraction(BaseModel):
    intent: Literal["order", "inquiry", "invoice_request", "confirmation", "other"] = Field(description="The primary intent of the user's message.")
    order_details: Optional[OrderExtraction] = Field(description="Extracted details if intent is order, inquiry, or confirmation.")


# --- Initialize LLM ---
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    api_key=settings.GROQ_API_KEY
)

# --- 2. Guardrail constants & Deterministic Parsers ---
AUTO_MATCH_THRESHOLD = 0.70    
MIN_CONFIRM_THRESHOLD = 0.35  

_GENERIC_WORDS = {
    "oil", "tel", "ka", "ki", "ke", "wala", "chahiye", "please", "do", "hai", "pukhraj",
    "carton", "cartons", "dibbe", "dibba", "dabba", "bhejo", "bhej", "ml", "gm", "kg", "pcs", "saman", "samaan"
}

_ALIASES = {
    "nariyal": "coconut", "tel": "oil", "oyl": "oil", "coknut": "coconut",
    "coconat": "coconut", "jasmin": "jasmine", "chameli": "jasmine",
    "amla": "amla", "thanda": "thanda", "navratna": "thanda",
    "bill": "invoice", "receipt": "invoice",
}

_VAGUE_REFERENCE_PATTERNS = [
    r'\bpurana\b', r'\bpurna\b', r'\bpichl[ae]\b', r'\bwahi\b', r'\bwoh wala\b',
    r'\bsame wala\b', r'\bprevious one\b', r'\bthat product\b', r'\bold one\b', r'\busual\b',
]

NAME_MATCH_UNKNOWN = 0.30
NAME_MATCH_CONFIDENT = 0.45
NAME_MATCH_MARGIN = 0.15
SKU_CONFIRM_THRESHOLD = 0.40


def _apply_aliases(raw_name: str) -> str:
    s = str(raw_name).lower()
    for k, v in _ALIASES.items():
        s = re.sub(rf'\b{k}\b', v, s)
    return s


def _similarity_score(search_term: str, target: str) -> float:
    target_words = set(target.split()) - _GENERIC_WORDS
    search_words = set(search_term.split()) - _GENERIC_WORDS
    if not target_words:
        target_words = set(target.split())
    overlap = target_words & search_words
    coverage = len(overlap) / len(target_words) if target_words else 0.0
    char_ratio = difflib.SequenceMatcher(None, search_term, target).ratio()
    return min(0.75 * coverage + 0.25 * char_ratio, 1.0)


def _is_vague_reference(text: str) -> bool:
    if not text:
        return False
    t = str(text).lower()
    return any(re.search(p, t) for p in _VAGUE_REFERENCE_PATTERNS)


def _match_product_family(raw_name: str, products: list):
    if not raw_name:
        return None, 0.0, [], 0.0
    search_term = _apply_aliases(raw_name)
    by_name = {}
    for p in products:
        by_name.setdefault(p.product_name, []).append(p)
    scored = [
        (name, _similarity_score(search_term, name.lower()), variants)
        for name, variants in by_name.items()
    ]
    if not scored:
        return None, 0.0, [], 0.0
    scored.sort(key=lambda x: x[1], reverse=True)
    best_name, best_score, best_variants = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0.0
    return best_name, best_score, best_variants, best_score - second_score


def _extract_size_ml(size_str):
    if not size_str:
        return None
    m = re.search(r'(\d+)\s*ml', str(size_str).lower())
    if m:
        return int(m.group(1))
    m2 = re.search(r'(\d+)', str(size_str))
    return int(m2.group(1)) if m2 else None


# --- Deterministic Yes/No confirmation detection ---
# NOTE: This MUST stay independent of the LLM. The confirmation-loop bug happened
# because a short reply like "haan" or "yes" was sometimes classified by the LLM
# as a different intent (e.g. "order"), so the pending confirmation was never
# resolved and the bot re-asked the same question. Yes/No detection for an
# already-pending confirmation must never depend on LLM intent classification.
_YES_TOKENS = {
    "yes", "y", "ha", "haa", "haan", "han", "ji", "haanji", "haan ji", "ok", "okay", "haaji",
}
_NO_TOKENS = {
    "no", "n", "na", "nah", "nahi", "nahin", "nahi ji", "nahiji", "nako", "nope",
}


def _detect_yes_no(user_text: str) -> Optional[bool]:
    """
    Token-based (not substring-based) Yes/No detection for pending confirmations.
    Returns True for YES, False for NO, None if unclear or ambiguous (contains
    both signals). Deliberately avoids `if "ha" in text` style matching, since
    that could false-positive on unrelated words.
    """
    if not user_text:
        return None
    # Normalize: lowercase, strip punctuation, collapse whitespace
    normalized = re.sub(r'[^\w\s]', ' ', str(user_text).lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return None

    tokens = normalized.split(" ")
    token_set = set(tokens)

    # Also check the full normalized phrase for known multi-word variants
    # like "haan ji" / "nahi ji" that might not match on single-token basis
    has_yes = bool(token_set & _YES_TOKENS) or normalized in _YES_TOKENS
    has_no = bool(token_set & _NO_TOKENS) or normalized in _NO_TOKENS

    # "nahi ji" contains "ji" (a YES token) and "nahi" (a NO token) - since
    # "nahi"/"nahin" is an explicit negation, NO must take precedence over a
    # trailing/accompanying "ji" in that specific combination.
    if has_no and has_yes:
        no_only_tokens = token_set & _NO_TOKENS
        yes_only_tokens = token_set & _YES_TOKENS
        if no_only_tokens and yes_only_tokens <= {"ji"}:
            return False
        # Genuinely mixed/ambiguous signal - do not guess.
        return None

    if has_no:
        return False
    if has_yes:
        return True
    return None


def _deterministic_slot_extraction(user_text: str) -> dict:
    """
    Deterministic fallback parser to catch obvious values (like '100ml' or '5 cartons')
    when a follow-up reply is short and sparse.
    """
    res = {}
    t = user_text.lower()
    
    # Extract size
    ml_match = re.search(r'(\d+)\s*ml', t)
    if ml_match:
        res["size"] = f"{ml_match.group(1)}ml"
        
    # Extract quantity cartons (handles '5 carton', '10 dibbe', etc.)
    qty_match = re.search(r'(\d+)\s*(carton|cartons|dibbe|dibba|dabba|pcs)', t)
    if qty_match:
        res["quantity_cartons"] = int(qty_match.group(1))
    elif not ml_match:
        # If just a plain number is given during slot collection, assume quantity if no quantity exists
        num_match = re.search(r'\b(\d+)\b', t)
        if num_match:
            res["quantity_cartons"] = int(num_match.group(1))
            
    return res


def _order_is_safe_to_create(product, quantity, family_score: float, margin: float) -> bool:
    if product is None or not getattr(product, "sku", None):
        return False
    if not quantity or quantity <= 0:
        return False
    if family_score < NAME_MATCH_CONFIDENT or margin < NAME_MATCH_MARGIN:
        return False
    return True


# --- Final completeness gate (must run immediately before EVERY
# order_service.process_draft_order call) ---
# Requirement: never place an order until ALL required fields are present.
# This function does NOT invent/default any value - it only reports what is
# missing so the caller can route back into collecting_order_info and ask
# for exactly those fields. No call site may bypass this check.
def _missing_required_order_fields(sku: Optional[str], quantity_cartons, payment_type: Optional[str],
                                     delivery_address: Optional[str], requested_delivery_date: Optional[str]) -> list:
    missing = []
    if not sku:
        missing.append("product")
    if not quantity_cartons or quantity_cartons <= 0:
        missing.append("quantity_cartons")
    if not payment_type:
        missing.append("payment_type")
    # delivery_address: only "DEFAULT"/"same"/"default" (an explicit user choice,
    # per OrderExtraction's own docstring: "If 'same' or 'default', return DEFAULT")
    # is an established valid value that resolves to None. Anything else missing
    # is NOT assumed - it must be asked for.
    if not delivery_address:
        missing.append("delivery_address")
    # requested_delivery_date: no existing business logic in this file defines
    # a user-unconfirmed absence as ASAP. The "or 'ASAP'" fallback that used to
    # sit right next to order creation was a silent default, not a confirmed
    # value, so it does not count as "established" and is not honored here.
    if not requested_delivery_date:
        missing.append("requested_delivery_date")
    return missing


_FIELD_PROMPTS = {
    "product": "which product you'd like",
    "quantity_cartons": "the quantity in cartons",
    "payment_type": "the payment type (credit / cod / prepaid)",
    "delivery_address": "the delivery address (or say 'same'/'default' to use your default address)",
    "requested_delivery_date": "the requested delivery date",
}


def _ask_for_missing_fields(missing: list) -> str:
    labels = [_FIELD_PROMPTS.get(f, f) for f in missing]
    return "Please provide " + ", ".join(labels) + "."


def _fuzzy_match_product(raw_name: str, size: str, products: list):
    if not raw_name:
        return None, 0.0
    search_term = _apply_aliases(raw_name)
    if size:
        search_term += f" {size}"
    best_match = None
    best_score = 0.0
    for p in products:
        target = f"{p.product_name.lower()} {p.size_ml}ml" if p.size_ml else p.product_name.lower()
        score = _similarity_score(search_term, target)
        if score > best_score:
            best_score = score
            best_match = p
    return best_match, min(best_score, 1.0)


async def process_message(state: AgentState):
    messages = state["messages"]
    sender_phone = "".join(filter(str.isdigit, state.get("sender_phone", "")))
    user_text = messages[-1].content
    
    user_text_normalized = re.sub(r'(\d+)\s+(ml|gm|kg|carton|pcs)', r'\1\2', user_text, flags=re.IGNORECASE)
    
    db = SessionLocal()
    try:
        distributor = db.query(Distributor).filter(Distributor.phone_number == sender_phone).first()
        if not distributor or distributor.status != "active":
            return {"messages": [AIMessage(content="Sorry, your account is not active or not registered. Please contact the Sales Manager.")]}

        memory = db.query(SessionMemory).filter(SessionMemory.phone_number == sender_phone).first()
        if not memory:
            memory = SessionMemory(
                phone_number=sender_phone,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.add(memory)
            db.commit()

        if memory.expires_at < datetime.now(timezone.utc):
            memory.current_state = None
            memory.slots = {}
            memory.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.commit()

        active_products = catalog_service.list_available_products(db)
        catalog_names = [f"{p.product_name} {p.size_ml}ml" for p in active_products]

        # ------------------------------------------------------------------
        # DETERMINISTIC CONFIRMATION HANDLING (must run BEFORE the LLM call)
        # ------------------------------------------------------------------
        # Root cause of the original bug: the LLM was called first and could
        # classify a short Yes/No reply (e.g. "haan", "yes") as some other
        # intent (e.g. "order"), so the pending confirmation was never
        # resolved and the same confirmation question got asked again.
        # A user's answer to an already-pending confirmation must be handled
        # purely with deterministic logic - never routed through the LLM.
        if memory.current_state == "pending_product_confirmation":
            is_yes = _detect_yes_no(user_text)

            if is_yes is True:
                pending = memory.slots.get("raw_extracted", {}) or {}
                confirmed_sku = memory.slots.get("confirmed_sku")

                if not confirmed_sku:
                    # Defensive guard: state exists but the exact SKU wasn't
                    # captured (e.g. stale/older session data). Never fall back
                    # to a best-guess product - clear and ask again.
                    logger.error(
                        "Pending confirmation for %s had no confirmed_sku in memory.slots", sender_phone
                    )
                    memory.current_state = None
                    memory.slots = {}
                    db.commit()
                    return {"messages": [AIMessage(content="Sorry, I lost track of which product we were confirming. Which product would you like?")]}

                # Resolve the EXACT SKU from the current active catalog.
                # NEVER fall back to active_products[0] or any other product -
                # the confirmation must resolve to precisely what was shown.
                confirmed_product = next((p for p in active_products if p.sku == confirmed_sku), None)

                if not confirmed_product:
                    logger.error(
                        "Confirmed SKU %s for %s is no longer available in active_products",
                        confirmed_sku, sender_phone
                    )
                    memory.current_state = None
                    memory.slots = {}
                    db.commit()
                    return {"messages": [AIMessage(content="Sorry, that product is no longer available. Please tell me which product you'd like instead.")]}

                qty = pending.get("quantity_cartons")
                if not qty or qty <= 0:
                    # Do NOT default to 1 or silently invent a quantity.
                    memory.current_state = "collecting_order_info"
                    memory.slots = {"pending_extracted": {**pending, "product_name": confirmed_product.product_name}}
                    db.commit()
                    return {"messages": [AIMessage(content=f"Got it - confirming {confirmed_product.product_name} {confirmed_product.size_ml}ml. How many cartons would you like?")]}

                addr = pending.get("delivery_address")
                date = pending.get("requested_delivery_date")
                payment_type = pending.get("payment_type")

                # --- FINAL COMPLETENESS GATE (confirmation-YES path) ---
                # Product + quantity are already known at this point (SKU was
                # confirmed above, quantity checked just above). Still must not
                # place the order if payment_type / delivery_address /
                # requested_delivery_date were never actually provided by the
                # user - the pre-existing "or 'ASAP'" / CREDIT-default fallback
                # is exactly the kind of silent assumption this gate forbids.
                still_missing = _missing_required_order_fields(
                    confirmed_product.sku, qty, payment_type, addr, date
                )
                # product/quantity are already confirmed at this point, so
                # only payment_type/address/date can legitimately still be missing.
                still_missing = [f for f in still_missing if f not in ("product", "quantity_cartons")]
                if still_missing:
                    memory.current_state = "collecting_order_info"
                    memory.slots = {"pending_extracted": {
                        **pending,
                        "product_name": confirmed_product.product_name,
                        "size": f"{confirmed_product.size_ml}ml",
                        "quantity_cartons": qty,
                        # carry over the exact confirmed SKU so the next turn
                        # can skip re-matching and go straight to order creation
                        "confirmed_sku": confirmed_product.sku,
                    }}
                    db.commit()
                    reply = "Product confirmed. " + _ask_for_missing_fields(still_missing)
                    return {"messages": [AIMessage(content=reply)]}

                pt_enum = PaymentType.CASH if payment_type == "cod" else PaymentType.CREDIT

                order_in = OrderCreate(
                    distributor_phone=sender_phone,
                    payment_type=pt_enum,
                    delivery_address=None if str(addr).upper() == "DEFAULT" else addr,
                    requested_delivery_date=date,
                    items=[OrderItemCreate(product_sku=confirmed_product.sku, quantity_cartons=qty)]
                )
                try:
                    saved_order = order_service.process_draft_order(db, order_in)
                    # Only clear pending state AFTER the order is successfully created.
                    memory.current_state = None
                    memory.slots = {}
                    db.commit()
                    reply = f"Successfully recorded! Order {saved_order.order_number} is now {saved_order.status} (Total: ₹{saved_order.total_amount})."
                except Exception as e:
                    logger.exception("Order creation failed during confirmation for %s", sender_phone)
                    # Preserve pending state so the user can retry safely -
                    # do not pretend the order was created.
                    reply = f"System Alert: {str(e)}"
                return {"messages": [AIMessage(content=reply)]}

            elif is_yes is False:
                memory.current_state = None
                memory.slots = {}
                db.commit()
                return {"messages": [AIMessage(content="Okay, let's start over. What product do you need?")]}

            else:
                # Neither a clear YES nor NO (or an ambiguous mixed reply) -
                # keep the pending state and ask again. Do NOT create an order.
                return {"messages": [AIMessage(content="Please reply with Yes/Haan or No/Nahi to confirm the product.")]}

        structured_llm = llm.with_structured_output(IntentAndExtraction)
        system_prompt = f"""
        You are AI-DOMS, an order assistant.
        Current active products: {catalog_names}.
        Categorize intent: 'order' (buy), 'inquiry' (price check), 'invoice_request' (wants bill/receipt), 'confirmation' (answering yes/no), 'other'.
        If 'confirmation', set 'is_yes'. Extract details if available. Do NOT guess SKUs.
        If the user refers to a product vaguely (e.g. "the usual", "same as last time", "purana wala",
        "old stuff") WITHOUT naming an actual product, leave product_name as null rather than inferring
        it from earlier messages. Never resolve a vague reference into a specific product yourself.
        """

        response = await structured_llm.ainvoke([SystemMessage(content=system_prompt)] + messages)

        intent = response.intent
        extracted = response.order_details.model_dump() if response.order_details else {}
        reply = "I didn't quite catch that. Could you please repeat?"

        if memory.current_state == "collecting_order_info":
            stored = memory.slots.get("pending_extracted", {}) or {}
            merged = dict(stored)
            
            # Blend LLM extraction with deterministic fallback extraction
            det_extracted = _deterministic_slot_extraction(user_text)
            for k, v in det_extracted.items():
                if v not in (None, "", []):
                    merged[k] = v

            for k, v in extracted.items():
                if v not in (None, "", []):
                    merged[k] = v
                    
            extracted = merged
            intent = "order"
            memory.current_state = None
            memory.slots = {}

        if intent == "invoice_request" or "invoice" in user_text.lower() or "bill" in user_text.lower() or "invois" in user_text.lower():
            latest_invoice = db.query(Invoice).join(Order).join(Distributor).filter(
                Distributor.phone_number == sender_phone
            ).order_by(Invoice.generated_at.desc()).first()

            if latest_invoice:
                reply = f"_INVOICE_TRIGGER_|{latest_invoice.id}"
            else:
                reply = "You don't have any recently approved orders with a generated invoice."

        elif intent == "inquiry":
            if not active_products:
                reply = "Our catalog is currently empty."
            else:
                prod_list = "\n".join([f"- {p.product_name} ({p.size_ml}ml): ₹{p.price_per_carton}/carton" for p in active_products])
                reply = f"Here is our current product catalog:\n{prod_list}"

        elif intent == "order":
            raw_name = extracted.get("product_name")
            size = extracted.get("size")
            qty = extracted.get("quantity_cartons")
            addr = extracted.get("delivery_address")
            date = extracted.get("requested_delivery_date")

            # Fast path: if we already resolved and confirmed an exact SKU on a
            # prior turn (carried over via collecting_order_info while waiting
            # on payment/address/date), use that SKU directly instead of
            # re-running fuzzy/family matching - guarantees the order can never
            # end up on a different SKU than the one already shown to the user.
            carried_sku = extracted.get("confirmed_sku")
            carried_product = None
            if carried_sku:
                carried_product = next((p for p in active_products if p.sku == carried_sku), None)
                if not carried_product:
                    logger.error("Carried confirmed_sku %s for %s is no longer available", carried_sku, sender_phone)
                    memory.current_state = None
                    memory.slots = {}
                    db.commit()
                    reply = "Sorry, that product is no longer available. Please tell me which product you'd like instead."
                    return {"messages": [AIMessage(content=reply)]}

            if carried_product:
                payment_type = extracted.get("payment_type")
                still_missing = _missing_required_order_fields(
                    carried_product.sku, qty, payment_type, addr, date
                )
                still_missing = [f for f in still_missing if f not in ("product", "quantity_cartons")]
                if not qty or qty <= 0:
                    still_missing = ["quantity_cartons"] + [f for f in still_missing if f != "quantity_cartons"]
                if still_missing:
                    memory.current_state = "collecting_order_info"
                    memory.slots = {"pending_extracted": {**extracted, "confirmed_sku": carried_product.sku}}
                    db.commit()
                    reply = _ask_for_missing_fields(still_missing)
                else:
                    pt_enum = PaymentType.CASH if payment_type == "cod" else PaymentType.CREDIT
                    order_in = OrderCreate(
                        distributor_phone=sender_phone,
                        payment_type=pt_enum,
                        delivery_address=None if str(addr).upper() == "DEFAULT" else addr,
                        requested_delivery_date=date,
                        items=[OrderItemCreate(product_sku=carried_product.sku, quantity_cartons=qty)]
                    )
                    try:
                        saved_order = order_service.process_draft_order(db, order_in)
                        reply = f"Successfully recorded! Order {saved_order.order_number} is now {saved_order.status} (Total: ₹{saved_order.total_amount})."
                        memory.current_state = None
                        memory.slots = {}
                        db.commit()
                    except Exception as e:
                        logger.exception("Order creation failed for carried SKU, %s", sender_phone)
                        reply = f"System Alert: {str(e)}"
                return {"messages": [AIMessage(content=reply)]}

            if _is_vague_reference(user_text) or _is_vague_reference(raw_name):
                reply = "Which product would you like? Please tell me the exact product name."
                memory.current_state = "collecting_order_info"
                memory.slots = {"pending_extracted": {
                    "quantity_cartons": qty,
                    "delivery_address": addr,
                    "requested_delivery_date": date,
                    "payment_type": extracted.get("payment_type"),
                }}
                db.commit()
            elif not raw_name or not qty:
                missing = []
                if not raw_name: missing.append("product name")
                if not qty: missing.append("quantity in cartons")
                reply = f"Please specify the {', '.join(missing)}."
                memory.current_state = "collecting_order_info"
                memory.slots = {"pending_extracted": extracted}
                db.commit()
            else:
                family_name, family_score, family_variants, margin = _match_product_family(raw_name, active_products)
                if not family_name or family_score < NAME_MATCH_UNKNOWN:
                    reply = f"I couldn't confidently find '{raw_name}' in our catalog. Let me escalate this to the Sales Manager."
                elif family_score < NAME_MATCH_CONFIDENT or margin < NAME_MATCH_MARGIN:
                    best_guess, guess_score = _fuzzy_match_product(raw_name, size, active_products)
                    if not best_guess or guess_score < SKU_CONFIRM_THRESHOLD:
                        reply = f"I couldn't confidently find '{raw_name}' in our catalog. Let me escalate this to the Sales Manager."
                    else:
                        memory.current_state = "pending_product_confirmation"
                        # Store the EXACT SKU that was shown to the user, not just the
                        # product family name - multiple sizes can share a product name,
                        # so re-resolving by name later could silently pick the wrong SKU.
                        memory.slots = {
                            "raw_extracted": extracted,
                            "confirmed_sku": best_guess.sku,
                            "confirmed_sku_name": best_guess.product_name,
                        }
                        db.commit()
                        reply = f"Aap {best_guess.product_name} {best_guess.size_ml}ml ki baat kar rahe hain? (Quantity: {qty}) Please reply Yes/Haan or No."
                else:
                    distinct_sizes = sorted({v.size_ml for v in family_variants if v.size_ml is not None})
                    best_match = None
                    if len(distinct_sizes) > 1 and not size:
                        options = ", ".join(f"{s}ml" for s in distinct_sizes)
                        reply = f"Aap {family_name} ka kaunsa size chahte hain? {options}"
                        memory.current_state = "collecting_order_info"
                        memory.slots = {"pending_extracted": {**extracted, "product_name": family_name}}
                        db.commit()
                    elif len(distinct_sizes) > 1 and size:
                        requested_ml = _extract_size_ml(size)
                        size_matches = [v for v in family_variants if v.size_ml == requested_ml]
                        if not size_matches:
                            options = ", ".join(f"{s}ml" for s in distinct_sizes)
                            reply = f"We don't have {family_name} in {size}. Available sizes: {options}."
                            memory.current_state = "collecting_order_info"
                            memory.slots = {"pending_extracted": {**extracted, "product_name": family_name, "size": None}}
                            db.commit()
                        else:
                            best_match = size_matches[0]
                    else:
                        best_match = family_variants[0]

                    if best_match:
                        if not _order_is_safe_to_create(best_match, qty, family_score, margin):
                            reply = "I need a bit more detail to safely place this order. Could you confirm the exact product, size, and quantity?"
                        else:
                            payment_type = extracted.get("payment_type")

                            # --- FINAL COMPLETENESS GATE (direct order path) ---
                            # Do not silently default payment_type to CREDIT or
                            # requested_delivery_date to "ASAP" - those must be
                            # explicit, user-provided values. Route to
                            # collecting_order_info for whatever is missing.
                            still_missing = _missing_required_order_fields(
                                best_match.sku, qty, payment_type, addr, date
                            )
                            still_missing = [f for f in still_missing if f not in ("product", "quantity_cartons")]
                            if still_missing:
                                memory.current_state = "collecting_order_info"
                                memory.slots = {"pending_extracted": {
                                    **extracted,
                                    "product_name": best_match.product_name,
                                    "size": f"{best_match.size_ml}ml",
                                    "quantity_cartons": qty,
                                    # carry over the exact resolved SKU so the next
                                    # turn can skip re-matching entirely
                                    "confirmed_sku": best_match.sku,
                                }}
                                db.commit()
                                reply = _ask_for_missing_fields(still_missing)
                            else:
                                pt_enum = PaymentType.CASH if payment_type == "cod" else PaymentType.CREDIT
                                order_in = OrderCreate(
                                    distributor_phone=sender_phone,
                                    payment_type=pt_enum,
                                    delivery_address=None if str(addr).upper() == "DEFAULT" else addr,
                                    requested_delivery_date=date,
                                    items=[OrderItemCreate(product_sku=best_match.sku, quantity_cartons=qty)]
                                )
                                try:
                                    saved_order = order_service.process_draft_order(db, order_in)
                                    reply = f"Successfully recorded! Order {saved_order.order_number} is now {saved_order.status} (Total: ₹{saved_order.total_amount})."
                                    memory.current_state = None
                                    memory.slots = {}
                                    db.commit()
                                except Exception as e:
                                    reply = f"System Alert: {str(e)}"

        return {"messages": [AIMessage(content=reply)]}

    except Exception as e:
        logger.exception("Error in process_message")
        return {"messages": [AIMessage(content="An internal system error occurred.")]}
    finally:
        db.close()


def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("process_message", process_message)
    workflow.add_edge(START, "process_message")
    workflow.add_edge("process_message", END)
    return workflow