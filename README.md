# DistribuFlow 🚀

**AI-Powered B2B Order Management System for WhatsApp**

> An AI-powered conversational WhatsApp bot that autonomously processes multi-modal distributor requests (text and voice), extracts key order parameters, triggers real-time alerts, and seamlessly handles automated PDF invoicing.

## 🌟 Overview

DistribuFlow (Internal Engine: AI-DOMS) modernizes the traditional B2B supply chain by replacing manual order entry with an intelligent, stateful WhatsApp agent. Built for scale and reliability, the system leverages deterministic fuzzy matching alongside LLM extraction to prevent hallucinations, ensuring that multi-thousand-rupee orders are never placed accidentally based on vague references or typos.

## ✨ Key Features

* **Multi-Modal WhatsApp Interface:** Natively processes both text messages and voice notes (via Whisper), understanding English, Hindi, and mixed Hinglish inputs.
* **Defense-in-Depth AI Architecture:**
* **Vague Reference Guardrails:** Automatically intercepts ambiguous phrases (e.g., *"purana wala saman"*) and forces the user to clarify instead of hallucinating past orders.
* **IDF-Weighted Fuzzy Matching:** Uses Term Frequency-Inverse Document Frequency (TF-IDF) scoring and alias mapping to handle severe typos (*"coknut oyl"* $\rightarrow$ *"Coconut Oil"*) without relying on unpredictable LLM guessing.


* **Stateful Conversational Memory:** Powered by LangGraph and PostgreSQL checkpoints, the bot remembers context across multi-turn conversations to collect missing slots (Size, Quantity, Payment Type, Address, Date) step-by-step.
* **Automated Invoice Delivery:** Real-time PDF invoice generation triggered via an Admin Dashboard approval, securely fetched and delivered back to the distributor as a WhatsApp Document via n8n.
* **Real-Time Admin Alerts:** Decoupled background webhooks instantly notify Sales Managers of newly drafted orders with exact financial totals.

## 🛠 Tech Stack

* **Backend System:** FastAPI, Python 3.10+, SQLAlchemy, PostgreSQL


* **AI / NLP Pipeline:** LangChain, LangGraph, Groq API (`llama-3.3-70b-versatile`), Whisper (Voice-to-Text)


* **Workflow Automation:** n8n (Self-Hosted Docker), Meta Graph API (WhatsApp Business Webhooks)


* **Frontend (Admin):** HTML/CSS (Minimalist Apple-style UI for order approvals)



---

## 🏗 Architecture Flow

1. **Intake:** WhatsApp webhook hits the **n8n workflow**.
2. **Pre-processing:** n8n filters out Meta status receipts (`sent`/`delivered`) and routes actual messages. Voice notes are downloaded and transcribed via Whisper.
3. **AI Agent Processing:** The text is sent to the **FastAPI** `/chat` endpoint.
4. **State Machine (LangGraph):**
* Normalizes units and extracts intent/slots via Groq LLM.
* Runs strict semantic guardrails and deterministic catalog matching.
* Updates PostgreSQL session memory for follow-up questions or creates a `Draft` Order.


5. **Fulfillment:** n8n catches backend trigger responses (like `_INVOICE_TRIGGER_|{id}`) to fetch generated PDFs and upload them to the Meta Graph API for chat delivery.

---

## 🚀 Installation & Setup

### 1. Prerequisites

* Python 3.10+


* PostgreSQL installed and running


* Docker & Docker Compose (for n8n)


* Meta Developer Account (WhatsApp Business API setup)



### 2. Clone the Repository

```bash
git clone https://github.com/technospes/DistribuFlow.git
cd DistribuFlow/backend

```

### 3. Environment Variables

Create a `.env` file in the `backend` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/distribuflow

# AI & APIs
GROQ_API_KEY=gsk_your_groq_api_key_here

# Meta / WhatsApp
WHATSAPP_TOKEN=your_meta_permanent_access_token
PHONE_NUMBER_ID=your_meta_phone_id
VERIFY_TOKEN=your_custom_webhook_verify_token

```

### 4. Database Setup & Seeding

Install dependencies and initialize the database schema:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run Alembic migrations
alembic upgrade head

# Seed the database with catalog items and your test distributor number
python backend/scripts/seed_data.py

```

### 5. Run the Application

```bash
# Start the FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

*(Ensure your n8n Docker container is running and your webhook URLs are tunneled via ngrok/localtunnel if testing locally).*

---

## 🧪 Usage / Testing the Bot

Once the system is live, send the following messages to your configured WhatsApp number to see the architecture in action:

1. **The Typo & Unit Test:** `"100 ml coknut oyl 5 carton bhej do"` $\rightarrow$ *Creates a draft order.*
2. **The Guardrail Test:** `"bhai woh purana wala saman 10 dibbe bhej do"` $\rightarrow$ *Rejects and asks for specific product name.*
3. **The Multi-Turn Memory Test:** `"Jasmine ka tel chahiye"` $\rightarrow$ *Bot asks for size.* $\rightarrow$ `"100ml"` $\rightarrow$ *Bot asks for quantity.*
4. **The Invoice Retrieval:** Approve an order on the Admin Dashboard, then text `"invoice bhejo"` $\rightarrow$ *Bot delivers `Tax_Invoice.pdf`.*

---

## 📁 Project Structure

Reflecting the precise directory layout of your repository:

```text
DistribuFlow/
├── backend/
│   ├── alembic/              # Database migration configurations & versions
│   ├── app/
│   │   ├── agents/           # LangGraph state machine & order_agent.py
│   │   ├── api/              # FastAPI routers (admin, chat, distributors, orders, webhook)
│   │   ├── config/           # App configuration setup
│   │   ├── core/             # Core application dependencies
│   │   ├── database/         # SQLAlchemy sessions, models, and checkpointing
│   │   ├── repositories/     # Database repository wrappers
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── services/         # Core business logic (catalog, invoice, order management)
│   ├── invoices_store/       # Generated PDF invoice documents
│   ├── scripts/              # Database seeding and demo reset scripts
│   ├── alembic.ini
│   ├── requirements.txt
│   └── test_agent.py
├── docs/                     # Documentation files
├── frontend/                 # Admin interface (admin_dashboard.html)
├── n8n/                      # n8n workflow configurations
├── docker-compose.yml
├── requirements.txt
└── README.md

```

---

## 👨‍💻 Author

**Ayush Shukla**

*AI Engineer*

Specializing in production-grade AI systems, Retrieval-Augmented Generation (RAG) pipelines, and multimodal agents.

[GitHub](https://github.com/technospes) | [LinkedIn](https://www.linkedin.com/in/ayushshukla-ar/)

---

*If you encounter any issues or have questions about the deterministic fuzzy matching architecture, feel free to open an issue!*
