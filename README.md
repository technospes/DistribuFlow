# DistribuFlow 🚀

**AI-Powered B2B Order Management System for WhatsApp**

> An agentic AI system that autonomously processes multi-modal distributor requests (text & voice) over WhatsApp, validates against real inventory and credit rules, and delivers automated PDF invoices.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20AI-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Source%20of%20Truth-336791.svg)](https://www.postgresql.org/)
[![n8n](https://img.shields.io/badge/n8n-Workflow%20Automation-EA4B71.svg)](https://n8n.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎥 Demo

### 📱 WhatsApp Bot Interaction

A distributor places an order conversationally. The bot resolves the product, collects missing slots (payment type, delivery date, address) across multiple turns, creates the order, and fires a real-time admin notification.

![WhatsApp Bot Interaction](./docs/whatsapp_screenshot.png)

> **What's happening above:**
> `"100 ml wala coconut 5 carton dedo"` → Bot asks for payment/delivery details → `"payment credit pe krna aur friday tak chahiye"` → Bot asks for address → `"same"` → **Order `ORD-20260814-00001` created as Draft (₹12000)** → Admin notification fired automatically.
>
> This single flow demonstrates: intent detection, stateful multi-turn memory, deterministic product resolution, credit validation, order creation, and decoupled event notifications.

### 🖥️ Admin Dashboard

Centralized interface for managing products, distributors, inventory, credit limits, orders, and approvals.

![Admin Dashboard](./docs/admin_dashboard.png)

### 🔄 End-to-End Flow

```
Distributor → WhatsApp → n8n → FastAPI → LangGraph → PostgreSQL
                                                          │
                                    ┌─────────────────────┼─────────────────────┐
                                    ▼                     ▼                     ▼
                             Inventory Validation   Credit Validation   Order Creation
                                                                              │
                                                                              ▼
                                                                     Invoice Generation
                                                                              │
                                                                              ▼
                                                                        WhatsApp PDF
```

---

## 🌟 Overview

DistribuFlow (Internal Engine: **AI-DOMS**) replaces manual B2B order entry with an intelligent, stateful WhatsApp agent. It combines **LLM-based language understanding** with **deterministic fuzzy matching and business validation** to ensure multi-thousand-rupee orders are never placed on hallucinated products or vague references.

Distributors communicate naturally in **Hindi, English, or Hinglish** via text or voice. On the company side, an Admin Dashboard manages distributors, products, inventory, orders, approvals, and operational data.

**Stack:** LangGraph (agentic orchestration) · FastAPI (backend) · PostgreSQL (source of truth) · n8n (event-driven WhatsApp automation).

---

## ✨ Key Features

**🧠 Agentic Order Processing**
LangGraph agent classifies intent (Order / Catalog inquiry / Invoice / Other) and extracts structured slots (product, size, quantity, payment type, address, delivery date) from free-form conversation.

**🗣️ Hindi / English / Hinglish Support**
Handles natural code-mixed inputs like `"bhai 100ml wala 5 carton"`, `"nariyal tel bhej do"`, or `"pichla bill send karna"` — no rigid command syntax required.

**🎙️ Voice-Based Ordering**
Voice notes are transcribed via Whisper and routed through the same agent pipeline.

**🎯 Deterministic Product Resolution**
> **The LLM understands the user's language. Python resolves the actual product.**

```
User message → LLM extracts name → PostgreSQL catalog → Normalization/aliases
→ IDF-weighted fuzzy matching → Size validation → Confidence decision → Actual SKU
```
`"Coknut oyl"` → `"Coconut Oil"` → 100ml → `PUKH-COCO-100`

**🛡️ Defense-in-Depth Guardrails**
- **Vague Reference Guardrails** intercept ambiguous phrases (e.g. *"purana wala saman"*) and force clarification instead of hallucinating.
- **IDF-Weighted Fuzzy Matching** handles severe typos (`"coknut oyl"`) without relying on LLM guessing.
- **Confidence Routing:** High → auto-resolve · Medium → confirm with distributor · Low → escalate.

**📦 Inventory & 💳 Credit Validation**
Every order checks real stock (full/partial/unavailable) and, for credit orders, compares `credit_used + order_amount` against `credit_limit` — routing to `OK` or `CREDIT HOLD`.

**📋 Controlled Order Lifecycle**
```
Draft → (Credit Validation) → OK / Credit Hold → Manager Approval → Approved → Invoice → WhatsApp
```

**🚨 Real-Time Admin Alerts**
Order creation fires a decoupled n8n webhook event. Notification failures never block order persistence.

**🧑‍💼 Admin Dashboard**
Manage orders (approve/cancel/filter), products (SKU, stock, pricing), and distributors (credit limits, status, history). All writes go through FastAPI — never directly to PostgreSQL.

**🧾 Automated Invoicing**
Approved orders trigger PDF generation. Distributors request invoices with `"invoice bhejo"` and receive the PDF directly in WhatsApp — scoped to their own `Distributor → Order → Invoice` relationship.

**💬 Stateful Memory**
LangGraph + PostgreSQL checkpoints preserve context across multi-turn slot-filling conversations.

---

## 🏗 Architecture

```
Distributor (WhatsApp Text/Voice)
        │
        ▼
      n8n  ──── filters status receipts, transcribes voice notes
        │
        ▼
    FastAPI  ─── REST API / Webhooks
        │
        ▼
   LangGraph  ─── Intent → Extraction → Resolution → Action
        │
        ▼
  Service Layer  ─── Catalog │ Order │ Distributor │ Invoice
        │
        ▼
 Repository Layer  ─── Product │ Distributor │ Order
        │
        ▼
   PostgreSQL  ─── Source of Truth
```

**Layered Responsibilities:**
- **AI Layer** — language understanding, intent detection, slot extraction, conversation.
- **Application Layer** — product resolution, inventory/credit validation, order creation, approval, invoicing.
- **Database Layer** — authoritative operational state.

The AI never touches inventory, credit, or SKUs directly — it delegates to deterministic Python services.

---

## 🔄 Complete Order Flow

1. Distributor sends WhatsApp message → **n8n** filters/routes it
2. Voice → Whisper transcription
3. **FastAPI** `/chat` endpoint receives text
4. **LangGraph** extracts intent + slots
5. Product resolved against PostgreSQL catalog (fuzzy match + SKU validation)
6. Inventory checked → Credit checked
7. Missing slots collected across turns
8. **Draft Order** created → stored in PostgreSQL
9. **n8n** notified → Sales Manager alerted
10. Manager reviews on Admin Dashboard → Approves / Cancels
11. Invoice PDF generated
12. Distributor requests invoice → PDF delivered via WhatsApp Document

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+ · PostgreSQL · Docker & Docker Compose (for n8n) · Meta WhatsApp Business Account

### 1. Clone & Create Environment

```bash
git clone https://github.com/technospes/DistribuFlow.git
cd DistribuFlow

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in `backend/`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/distribuflow
GROQ_API_KEY=gsk_your_groq_api_key_here

WHATSAPP_TOKEN=your_meta_permanent_access_token
META_ACCESS_TOKEN=your_meta_access_token
PHONE_NUMBER_ID=your_meta_phone_id
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_custom_webhook_verify_token

N8N_WEBHOOK_URL=http://localhost:5678/webhook/admin-alert
```

> ⚠️ Never commit `.env` or API keys.

### 3. Database Setup

```sql
CREATE DATABASE distribuflow;
```

```bash
cd backend
alembic upgrade head
python scripts/seed_data.py       # Seeds catalog + test distributor
```

### 4. Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`
- Dashboard: open `frontend/admin_dashboard.html`
- Ensure n8n is running; tunnel webhooks via ngrok for local testing.

---

## 🧪 Testing the Bot

Send these to your configured WhatsApp number:

| Scenario | Input | Expected |
|---|---|---|
| Typo + units | `"100 ml coknut oyl 5 carton bhej do"` | Draft order created |
| Vague reference | `"bhai woh purana wala saman 10 dibbe bhej do"` | Rejected, asks for specific product |
| Multi-turn memory | `"Jasmine ka tel chahiye"` → `"100ml"` → `"5"` | Bot fills slots step-by-step |
| Invoice retrieval | `"invoice bhejo"` after approval | `Tax_Invoice.pdf` delivered |
| Ambiguous product | `"Jasmin ke 2 carton"` | Confirmation prompt |
| Unknown product | `"XYZ product ke 10 carton"` | No SKU invented |

Agent test script: `python backend/test_agent.py`

---

## 📁 Project Structure

```text
DistribuFlow/
├── backend/
│   ├── alembic/                # Migrations
│   ├── app/
│   │   ├── agents/             # LangGraph state machine (order_agent.py, state.py)
│   │   ├── api/                # Routers: admin, chat, distributors, orders, products, webhook
│   │   ├── config/             # App configuration
│   │   ├── core/               # Dependencies
│   │   ├── database/           # Sessions, models, checkpointing
│   │   ├── repositories/       # DB wrappers
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # catalog · distributor · invoice · order
│   ├── invoices_store/         # Generated PDFs
│   ├── scripts/seed_data.py
│   ├── seed_db.py
│   ├── test_agent.py
│   ├── requirements.txt
│   └── alembic.ini
├── docs/                       # Screenshots & demo assets
├── frontend/admin_dashboard.html
├── n8n/                        # Workflow configs
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🗄 Database Design

```
Distributor ──places──▶ Order ──┬──▶ Order Items ──▶ Product
                                └──▶ Invoice
```

| Entity | Key Fields |
|---|---|
| **Distributor** | company, owner, phone, address, credit_limit, credit_used, status |
| **Product** | SKU, name, size, price/carton, stock, active |
| **Order** | order_number, distributor, status, credit_status, total, payment_type, delivery info, approval |
| **Order Item** | product, quantity, fulfilled_qty, price, subtotal, availability |
| **Invoice** | linked to approved orders |

---

## 🔌 API Endpoints

```
Products:      GET /api/products/                GET /api/products/{sku}
               POST /api/admin/products          PATCH /api/admin/products/{sku}/stock

Distributors:  GET /api/distributors/            POST /api/admin/distributors
               PATCH /api/admin/distributors/{phone}/credit

Orders:        GET /api/orders/                  GET /api/orders/{id}
               POST /api/orders/                 POST /api/orders/{id}/approve
                                                 POST /api/orders/{id}/cancel

Chat:          POST /api/chat/...
Invoice:       GET  /api/chat/download-invoice/{invoice_id}
Webhooks:      POST /api/webhook/...
```

---

## 📜 Business Rules

1. Only **active** distributors can place orders.
2. Credit orders validated against `credit_limit` → `OK` or `CREDIT HOLD`.
3. Requested quantities checked against available stock.
4. Low-confidence product matches never auto-create orders.
5. Order creation is delegated to the deterministic order service.
6. Invoices generated only for approved orders.
7. Order numbers follow `ORD-YYYYMMDD-#####`.
8. Only valid state transitions can cancel an order.
9. Invoice access scoped to the requesting distributor.
10. AI never modifies inventory or credit master data.

---

## 🧭 Design Principles

- **Separation of Concerns** — AI, API, services, repositories, DB, and automation are distinct.
- **PostgreSQL as Source of Truth** — always authoritative.
- **Deterministic Business Logic** — critical decisions in Python, not the LLM.
- **Human-in-the-Loop** — managers approve operational actions.
- **Event-Driven Automation** — n8n owns external communication workflows.
- **Conversational Interface** — no new UI to learn for distributors.
- **Extensibility** — ready for ERP, CRM, payments, logistics, Slack, email integrations.

---

## ⚙️ n8n Workflows

**Incoming Message:** `WhatsApp → n8n → FastAPI → LangGraph → n8n → WhatsApp`

**New Order Alert:** `FastAPI → n8n → Notification → Sales Manager`

**Invoice Delivery:** `"invoice bhejo" → LangGraph → Invoice Trigger → n8n → PDF Endpoint → Meta /media → WhatsApp Document`

---

## 📱 WhatsApp Integration

Requires a Meta App, WhatsApp Business Account, Phone Number ID, Access Token, and configured Webhook with appropriate permissions. Store credentials in environment variables or n8n credentials — **never in source code**.

---

## 🗺 Roadmap

**✅ Completed**
WhatsApp order intake · LangGraph agent · Intent classification · Structured extraction · Hindi/English/Hinglish · Voice (Whisper) · PostgreSQL · Catalog · Inventory validation · Credit validation · Delivery slots · Draft & Credit Hold · Approval workflow · Cancellation · PDF invoices · Invoice retrieval & WhatsApp delivery · n8n automation · Admin dashboard · Product/Distributor/Stock/Credit management · Order filtering · Fuzzy matching · Vague reference guardrails · Stateful memory

**🔮 Future**
Distributor-specific pricing · Inventory/credit adjustment history · Auth + RBAC · Audit logs · Analytics · Sales forecasting · Auto-reorder · Logistics/ERP integration · Multi-warehouse · Multi-language · Cloud deployment · Automated AI evaluation pipeline

**Potential V2 — Pricing Layer**
```
Distributor → Pricing Engine ─┬─▶ Standard Price
                              └─▶ Distributor Override
                                        │
                                        ▼
                                 Final Order Price
```

---

## 🎯 Current Scope

DistribuFlow is an **MVP / prototype-grade** system demonstrating the complete AI-assisted distributor ordering workflow. Production deployment requires: authentication & authorization, secrets management, HTTPS, hardened DB config, audit logging, monitoring, rate limiting, retries, queue-based background jobs, automated tests, and RBAC.

---

## 💡 Why DistribuFlow?

Traditional distributor ordering is fragmented across phone calls, WhatsApp messages, manual order entry, spreadsheets, and manual credit/invoice handling. DistribuFlow consolidates everything into a **single connected order lifecycle** — from conversational request to approved order and invoice delivery — while keeping critical business logic deterministic and human-supervised.

---

## 🌟 Key Highlights

| Capability | Technology |
|---|---|
| Conversational AI | LangGraph + Llama 3.3 70B |
| LLM Provider | Groq |
| Backend | FastAPI |
| Database / ORM / Migrations | PostgreSQL / SQLAlchemy / Alembic |
| Automation & Messaging | n8n · WhatsApp Cloud API |
| Admin UI | HTML / JavaScript / Tailwind |
| Voice Processing | Whisper |
| Product Resolution | IDF-weighted deterministic fuzzy matching |
| Invoicing | Automated PDF generation |
| State Memory | LangGraph + PostgreSQL checkpoints |

---

## 📄 License

MIT License

---

## 👨‍💻 Author

**Ayush Shukla** — *AI Engineer*
Specializing in production-grade AI systems, RAG pipelines, and multimodal agents.

[GitHub](https://github.com/technospes) · [LinkedIn](https://www.linkedin.com/in/ayushshukla-ar/)

---

*Questions about the deterministic fuzzy matching architecture? Open an issue.*

---
