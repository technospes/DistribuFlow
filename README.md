# DistribuFlow — AI-Powered Distributor Order Management System
 
An agentic AI-powered Distributor Order Management System that automates conversational order processing through WhatsApp while providing centralized inventory, credit, approval, notification, and invoice management.
 
DistribuFlow transforms the traditional distributor ordering process into an AI-driven, end-to-end order management workflow.
 
Distributors can communicate naturally through WhatsApp using text or voice messages. The Agentic AI layer understands Hindi, English, and Hinglish, extracts order requirements, resolves product names against the real catalog, validates inventory and credit rules, and creates orders in PostgreSQL.
 
On the company side, an Admin Dashboard provides a centralized interface for managing distributors, products, inventory, orders, approvals, and operational data.
 
The system uses **LangGraph** for agentic orchestration, **FastAPI** for backend services, **PostgreSQL** as the source of truth, and **n8n** for event-driven WhatsApp automation and notifications.
 
---
 
## Demo
 
**Distributor → AI → Order → Manager → Approval → Invoice**
 
```
Distributor
     │
     │ WhatsApp Text / Voice
     ▼
┌─────────────────────┐
│   WhatsApp / Meta    │
└──────────┬────────────┘
           │
           ▼
┌─────────────────────┐
│         n8n          │
│ Workflow Automation  │
└──────────┬────────────┘
           │
           ▼
┌─────────────────────┐
│       FastAPI        │
│       Webhook        │
└──────────┬────────────┘
           │
           ▼
┌─────────────────────┐
│      LangGraph       │
│    Agentic Layer     │
└──────────┬────────────┘
           │
           ▼
┌─────────────────────┐
│      PostgreSQL      │
│    Source of Truth   │
└──────────┬────────────┘
           │
           ├──────────────► Inventory Validation
           │
           ├──────────────► Credit Validation
           │
           ├──────────────► Order Creation
           │
           └──────────────► Invoice Generation
                               │
                               ▼
                          WhatsApp PDF
```
 
---
 
## Features
 
### 🤖 Agentic AI Order Processing
 
DistribuFlow uses a LangGraph-based agent to understand natural-language distributor requests. The distributor does not need to follow a rigid command format.
 
Examples:
- "Coconut oil ke 5 carton bhej do"
- "100ml wala coconut oil chahiye"
- "Friday ko delivery kar dena"
- "pichla invoice bhejo"
- "bill bhejo"
- "amla oil ka rate kya hai?"
The agent determines whether the request is:
- Order
- Product/catalog inquiry
- Invoice request
- Other
### 🗣️ Hindi, English & Hinglish Support
 
The AI is designed to understand conversational distributor communication in English, Hindi, and Hinglish.
 
Examples:
- "Coconut oil chahiye"
- "5 carton nariyal tel bhejo"
- "bhai 100ml wala 5 carton"
- "invoice bhej do"
- "pichla bill send karna"
This makes the system much closer to how distributors actually communicate instead of forcing structured forms.
 
### 🎙️ Voice-Based Ordering
 
Distributors can send voice notes through WhatsApp. The workflow is:
 
```
Voice Note
    ↓
Speech-to-Text
    ↓
LangGraph Agent
    ↓
Intent Detection
    ↓
Order Extraction
    ↓
Business Validation
    ↓
Order Creation
```
 
This allows distributors to place orders without typing.
 
### 🧠 Agentic Order Understanding
 
The AI extracts structured information from conversational messages. For an order, the system can identify:
 
- Product
- Product size
- Quantity
- Payment type
- Delivery address
- Requested delivery date
For example:
 
```
"Coconut oil 100ml ke 5 carton
Friday ko registered address pe bhejna."
```
 
becomes conceptually:
 
```json
{
  "product": "Coconut Oil",
  "size": "100ml",
  "quantity": 5,
  "delivery_address": "DEFAULT",
  "requested_delivery_date": "Friday"
}
```
 
The extracted information is then passed to deterministic backend business logic.
 
### 🎯 Deterministic Product Resolution
 
A major design principle of DistribuFlow is:
 
> The LLM understands the user's language. Python resolves the actual product.
 
The system does not allow the LLM to freely hallucinate SKUs. Instead:
 
```
User message
     ↓
LLM extracts product name
     ↓
Real PostgreSQL catalog
     ↓
Normalization / aliases
     ↓
Fuzzy matching
     ↓
Size validation
     ↓
Confidence decision
     ↓
Actual SKU
```
 
For example:
 
```
"Coknut oil" → "Coconut Oil" → 100ml → PUKH-COCO-100
```
 
This separates natural-language understanding from business-critical product identification.
 
### 📊 Confidence-Based Product Matching
 
Product matching uses confidence-based routing rather than blindly accepting every AI interpretation.
 
Conceptually:
- **High confidence** → Automatic product resolution
- **Medium confidence** → Ask distributor for confirmation
- **Low confidence** → Clarification / Human escalation
Example:
 
> **Distributor:** "Jasmin ke 2 carton"
> **Bot:** "Did you mean Jasmine Oil 100ml? Please reply Yes or No."
 
This reduces the risk of incorrect orders caused by spelling mistakes or noisy voice transcription.
 
### 📦 Real-Time Product & Inventory Validation
 
PostgreSQL acts as the operational source of truth. The order service validates:
 
- Product existence
- SKU
- Product price
- Available stock
- Requested quantity
- Availability status
Example:
 
| Requested | Available | Result  |
|-----------|-----------|---------|
| 10 cartons | 6 cartons | PARTIAL |
 
The AI does not independently modify inventory. Inventory remains controlled by the company's operational/admin layer.
 
### 💳 Credit Limit Validation
 
For credit-based orders, DistribuFlow checks the distributor's credit position before creating the order.
 
Conceptually:
 
```
Current Credit Used + New Order Amount
                ↓
    Compare with Credit Limit
                ↓
    Within Limit → OK
    Over Limit   → CREDIT HOLD
```
 
This allows the system to automatically identify orders that require managerial attention.
 
### 📋 Order Lifecycle
 
Orders follow a controlled business workflow.
 
```
                ┌───────────────┐
                │     Draft      │
                └───────┬────────┘
                        │
             Credit validation
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
             OK              Credit Hold
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
                     Manager
                     Approval
                        │
                        ▼
                     Approved
                        │
                        ▼
                Invoice Generated
                        │
                        ▼
              Invoice via WhatsApp
```
 
Orders can also be cancelled when permitted by the business rules.
 
### 🚨 Real-Time Order Notifications
 
When a new order is created, the system sends an event to an n8n webhook.
 
Example event:
 
```json
{
  "event": "new_order",
  "distributor_phone": "XXXXXXXXXX",
  "order_number": "ORD-20260810-00002",
  "total_amount": 13000,
  "status": "Draft",
  "requested_delivery_date": "Friday"
}
```
 
n8n then handles the notification workflow.
 
Example notification:
 
```
🚨 NEW ORDER RECEIVED
 
Distributor: ABC Distributors
Order: ORD-20260810-00002
Amount: ₹13,000
Status: Draft
Requested Delivery: Friday
```
 
The notification layer is deliberately decoupled from the core order transaction. If the notification system is temporarily unavailable, the order itself can still be persisted.
 
### 🧑‍💼 Admin Dashboard
 
DistribuFlow includes a dedicated web-based operational dashboard. The dashboard allows authorized company personnel to monitor and manage:
 
**Orders**
- Order number, distributor, amount, payment type, credit status, order status, requested delivery date
- Order details: product quantities, availability, order timeline
- Approval / cancellation
**Products**
- SKU, product name, size, price, available stock, active/inactive status
**Distributors**
- Company name, owner, phone number, address, credit limit, credit used, distributor status, order history
### 🔎 Dashboard Search & Filtering
 
The dashboard supports operational filtering such as:
- Draft orders
- Credit Hold orders
- Approved orders
- Cancelled orders
- Credit-based orders
- Other payment types
- Date-based order filtering
It also provides search functionality for quickly locating operational records.
 
### ➕ Admin Data Management
 
The dashboard provides creation workflows for operational entities such as:
- `+ Add Product`
- `+ Add Distributor`
- `+ Create Order`
These actions go through FastAPI APIs rather than directly manipulating PostgreSQL from the frontend.
 
```
Admin Dashboard → FastAPI → Business/API Layer → PostgreSQL
```
 
This maintains a clean separation between the frontend and database.
 
### 📦 Product Management
 
Administrators can create products with information such as:
- SKU
- Product Name
- Size
- Price / Carton
- Initial Stock
Stock can also be updated through the admin API:
 
```
PATCH /api/products/{sku}/stock
```
 
The AI itself does not directly modify stock.
 
### 👥 Distributor Management
 
Administrators can create and manage distributors with information such as:
- Company Name
- Owner Name
- Phone Number
- Address
- Credit Limit
- Status
Distributor status can include: `lead`, `active`, `inactive`.
 
Only active distributors are allowed to proceed through the relevant order-processing workflow.
 
### 🧾 Automated Invoice Generation
 
When an authorized person approves an order:
 
```
Order Approved → Invoice Service → PDF Generation → Invoice Stored
```
 
The generated invoice contains order-related information such as:
- Order number
- Distributor details
- Products
- Quantities
- Prices
- Subtotals
- Total amount
### 📲 Invoice Delivery Through WhatsApp
 
A distributor can simply say "invoice bhejo" or "pichla bill bhejo". The agent identifies `invoice_request`. The backend then finds the latest relevant invoice for that distributor.
 
The workflow becomes:
 
```
Distributor
     │
     │ "invoice bhejo"
     ▼
WhatsApp
     ↓
n8n
     ↓
FastAPI
     ↓
LangGraph
     ↓
Distributor-specific Invoice Lookup
     ↓
PDF Download
     ↓
Meta WhatsApp /media
     ↓
WhatsApp Document Message
     ↓
Distributor receives PDF
```
 
The invoice is therefore delivered as an actual WhatsApp document rather than simply returning a URL.
 
### 🔐 Distributor-Specific Invoice Access
 
Invoice retrieval is tied to the distributor's identity/context. The system does not simply allow `invoice_id → download`. Instead, it verifies the relationship between:
 
```
Distributor → Order → Invoice
```
 
This prevents a distributor from arbitrarily requesting another distributor's invoice.
 
---
 
## Architecture
 
DistribuFlow follows a layered architecture.
 
```
┌────────────────────────────────────────────┐
│                Distributor                  │
│            WhatsApp Text/Voice               │
└──────────────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────┐
│                     n8n                      │
│        WhatsApp Workflow Automation          │
└──────────────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────┐
│                  FastAPI                     │
│             REST API / Webhooks               │
└──────────────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────┐
│                 LangGraph                     │
│              Agentic AI Layer                 │
│  Intent → Extraction → Resolution → Action    │
└──────────────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────┐
│               Service Layer                   │
│  Catalog │ Order │ Distributor │ Invoice      │
└──────────────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────┐
│             Repository Layer                  │
│      Product │ Distributor │ Order            │
└──────────────────────┬───────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────┐
│                PostgreSQL                     │
│              Source of Truth                  │
└────────────────────────────────────────────┘
```
 
### 🧠 Agent Architecture
 
The LangGraph agent is separated into distinct responsibilities.
 
```
Incoming Message
       ↓
Analyze Message
       ↓
Intent + Structured Extraction
       ↓
Business Logic
       ↓
Catalog / Order / Invoice Service
       ↓
Response
```
 
The AI does not directly perform arbitrary database operations. Instead, the agent delegates to deterministic application services. This provides a separation between:
 
**AI Layer** — Responsible for:
- Understanding natural language
- Intent classification
- Information extraction
- Conversational interaction
**Application Layer** — Responsible for:
- Product resolution
- Inventory validation
- Credit validation
- Order creation
- Approval
- Invoice generation
**Database Layer** — Responsible for:
- Persistent operational state (products, distributors, orders, order items, invoices)
### 🔄 Complete Order Flow
 
A typical order follows this workflow:
 
1. Distributor sends WhatsApp message
2. n8n receives the event
3. FastAPI webhook receives message
4. Voice is transcribed if required
5. LangGraph analyzes the conversation
6. Intent is identified
7. Order information is extracted
8. Product is resolved against PostgreSQL catalog
9. Product size/SKU is validated
10. Inventory is checked
11. Credit limit is checked
12. Delivery information is collected
13. Order is created
14. PostgreSQL stores the order
15. n8n receives new-order event
16. Sales Manager receives notification
17. Manager reviews order
18. Manager approves/cancels order
19. Invoice is generated
20. Distributor requests invoice
21. n8n downloads invoice
22. Meta receives PDF
23. Distributor receives invoice on WhatsApp
---
 
## Tech Stack
 
| Layer | Technologies |
|---|---|
| AI / Agentic Layer | Python, LangChain, LangGraph, Groq, Llama 3.3 70B |
| Backend | FastAPI, SQLAlchemy, Pydantic, Alembic, Uvicorn |
| Database | PostgreSQL |
| Automation | n8n, WhatsApp / Meta Cloud API |
| Frontend | HTML, CSS, JavaScript, Tailwind CSS (Admin Dashboard) |
| Document Generation | Python PDF generation, automated invoice generation |
| Development / Infrastructure | Git, GitHub, Docker / Docker Compose, Python Virtual Environment |
 
---
 
## Project Structure
 
```
DistribuFlow/
│
├── backend/
│   │
│   ├── alembic/
│   │   ├── versions/
│   │   │   ├── 1e4d9e996e1b_initial_schema_setup.py
│   │   │   └── 75073b3d4b8c_add_requested_delivery_date.py
│   │   ├── env.py
│   │   └── script.py.mako
│   │
│   ├── app/
│   │   ├── agents/
│   │   │   ├── order_agent.py
│   │   │   └── state.py
│   │   │
│   │   ├── api/
│   │   │   ├── admin.py
│   │   │   ├── chat.py
│   │   │   ├── distributors.py
│   │   │   ├── orders.py
│   │   │   ├── products.py
│   │   │   └── webhook.py
│   │   │
│   │   ├── config/
│   │   │   └── config.py
│   │   │
│   │   ├── core/
│   │   │   └── dependencies.py
│   │   │
│   │   ├── models/
│   │   │   └── order.py
│   │   │
│   │   ├── repositories/
│   │   │   ├── distributor_repository.py
│   │   │   ├── order_repository.py
│   │   │   └── product_repository.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── distributor.py
│   │   │   ├── order.py
│   │   │   ├── product.py
│   │   │   └── webhook.py
│   │   │
│   │   └── services/
│   │       ├── catalog_service.py
│   │       ├── distributor_service.py
│   │       ├── invoice_service.py
│   │       └── order_service.py
│   │
│   ├── scripts/
│   │   └── seed_data.py
│   │
│   ├── seed_db.py
│   ├── test_agent.py
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   └── admin_dashboard.html
│
├── docker-compose.yml
├── requirements.txt
├── structure.txt
├── .gitignore
└── README.md
```
 
---
 
## Database Design
 
PostgreSQL acts as the single source of truth for operational data. The system revolves around entities such as:
 
```
Distributor
     │
     │ places
     ▼
   Order
     │
     ├───────────────┐
     │               │
     ▼               ▼
Order Items       Invoice
     │
     ▼
  Product
```
 
**Distributor** — ID, company name, owner, phone, address, credit limit, credit used, status
 
**Product** — Product ID, SKU, product name, size, price per carton, available stock, active status
 
**Order** — Order ID, order number, distributor, status, credit status, total amount, payment type, delivery address, requested delivery date, remarks, approval information
 
**Order Item** — Product, quantity, fulfilled quantity, price, subtotal, availability status
 
**Invoice** — Invoice-related information associated with approved orders
 
---
 
## Important API Endpoints
 
The backend exposes REST APIs for operational functionality.
 
**Products**
```
GET    /api/products/
GET    /api/products/{sku}
POST   /api/admin/products
PATCH  /api/admin/products/{sku}/stock
```
 
**Distributors**
```
GET    /api/distributors/
POST   /api/admin/distributors
PATCH  /api/admin/distributors/{phone}/credit
```
 
**Orders**
```
GET    /api/orders/
GET    /api/orders/{order_id}
POST   /api/orders/
POST   /api/orders/{order_id}/approve
POST   /api/orders/{order_id}/cancel
```
 
**AI / Chat**
```
POST   /api/chat/...
```
 
**Invoice**
```
GET    /api/chat/download-invoice/{invoice_id}
```
 
**Webhooks**
```
POST   /api/webhook/...
```
 
> Exact routes can vary depending on the router prefixes configured in `main.py`.
 
---
 
## Environment Variables
 
Create a `.env` file inside the backend environment/configuration used by the application.
 
```env
DATABASE_URL=postgresql://username:password@localhost:5432/distribuflow
GROQ_API_KEY=your_groq_api_key
META_ACCESS_TOKEN=your_meta_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
N8N_WEBHOOK_URL=http://localhost:5678/webhook/admin-alert
```
 
> Never commit `.env` or API keys to GitHub.
 
---
 
## Installation
 
### 1. Clone the repository
 
```bash
git clone https://github.com/technospes/DistribuFlow.git
cd DistribuFlow
```
 
### 2. Create Python virtual environment
 
```bash
python -m venv venv
```
 
Windows:
```bash
venv\Scripts\activate
```
 
Linux / macOS:
```bash
source venv/bin/activate
```
 
### 3. Install dependencies
 
```bash
pip install -r requirements.txt
```
 
If backend dependencies are maintained separately:
 
```bash
pip install -r backend/requirements.txt
```
 
---
 
## PostgreSQL Setup
 
Create a PostgreSQL database:
 
```sql
CREATE DATABASE distribuflow;
```
 
Then configure the connection string in `.env`:
 
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/distribuflow
```
 
---
 
## Run Database Migrations
 
DistribuFlow uses Alembic for database schema management.
 
From the backend directory:
 
```bash
cd backend
alembic upgrade head
```
 
For future schema changes:
 
```bash
alembic revision --autogenerate -m "description of change"
alembic upgrade head
```
 
---
 
## Seed Initial Data
 
The project includes seed scripts for populating development data.
 
```bash
python seed_db.py
```
 
or:
 
```bash
python scripts/seed_data.py
```
 
This can be used to populate initial products, distributors, inventory, and development records.
 
---
 
## Run FastAPI
 
From the backend directory:
 
```bash
uvicorn app.main:app --reload
```
 
The API will be available at: `http://localhost:8000`
 
FastAPI documentation: `http://localhost:8000/docs`
 
---
 
## Run the Admin Dashboard
 
Open `frontend/admin_dashboard.html`.
 
The dashboard communicates with the FastAPI backend. Make sure FastAPI is running before using the dashboard.
 
---
 
## n8n Configuration
 
DistribuFlow uses n8n as the workflow automation layer. Typical workflows include:
 
**Incoming WhatsApp Message**
```
WhatsApp → n8n Webhook → FastAPI → LangGraph → Response → n8n → WhatsApp
```
 
**New Order Notification**
```
FastAPI → n8n Admin Webhook → Notification Workflow → Sales Manager
```
 
**Invoice Delivery**
```
Distributor → "invoice bhejo" → LangGraph → Invoice Trigger → n8n
  → FastAPI PDF Endpoint → Meta /media → WhatsApp Document
```
 
---
 
## WhatsApp Integration
 
The WhatsApp integration uses Meta's WhatsApp Cloud API. The system requires configuration of:
 
- Meta App
- WhatsApp Business Account
- Phone Number ID
- Access Token
- Webhook
- Appropriate permissions
The Meta credentials should be stored securely through environment variables or n8n credentials rather than hardcoded in source code.
 
---
 
## Testing
 
The project includes an agent test script:
 
```bash
python backend/test_agent.py
```
 
Testing should cover both normal and adversarial conversational inputs:
 
| Scenario | Example Input | Expected Behavior |
|---|---|---|
| Basic order | "Coconut oil 100ml ke 5 carton chahiye" | Order created |
| Hinglish | "bhai nariyal tel ke 5 carton bhej do" | Order created |
| Typo | "Coknut oil 5 carton" | Product resolved via fuzzy matching |
| Missing information | "Coconut oil chahiye" | Bot asks for missing information |
| Invoice | "invoice bhejo" | Latest invoice sent |
| Hindi invoice request | "pichla bill bhej do" | Latest invoice sent |
| Ambiguous product | "Jasmin ke 2 carton" | Bot asks for confirmation |
| Invalid/unknown product | "XYZ product ke 10 carton" | Bot should not invent a SKU |
 
---
 
## Business Rules
 
DistribuFlow keeps business-critical operations outside the LLM wherever possible.
 
1. **Distributor Validation** — Only valid/active distributors can place orders.
2. **Credit Validation** — Credit orders are checked against the distributor's credit position.
3. **Inventory Validation** — Requested quantities are compared against available stock.
4. **Confidence Routing** — Uncertain product resolution should not blindly create an order.
5. **Controlled Order Creation** — The AI delegates order creation to the order service.
6. **Invoice Generation** — Approved orders trigger invoice generation.
7. **Product Pricing** — The current MVP uses the configured product pricing model. Distributor-specific negotiated pricing can be introduced as a future extension.
8. **Order Number Generation** — Orders receive structured identifiers such as `ORD-20260810-00002`.
9. **Approval** — Orders require the appropriate operational approval before becoming approved orders.
10. **Cancellation** — Only valid order states can be cancelled.
11. **Invoice Security** — Invoice access is associated with the requesting distributor.
12. **Human-Controlled Master Data** — AI does not independently modify operational inventory or credit records.
13. **Distributor Status** — Distributor lifecycle is controlled by the operational/admin system.
---
 
## Separation of Responsibilities
 
One of the most important architectural decisions in DistribuFlow is keeping AI away from authoritative business decisions.
 
```
┌─────────────────────┐
│         LLM           │
│                        │
│ Understand language    │
│ Detect intent          │
│ Extract information    │
└──────────┬─────────────┘
           │
           ▼
┌─────────────────────┐
│       Python           │
│                        │
│ Resolve SKU            │
│ Validate stock         │
│ Validate credit        │
│ Create order           │
└──────────┬─────────────┘
           │
           ▼
┌─────────────────────┐
│     PostgreSQL         │
│                        │
│ Source of truth        │
└─────────────────────┘
```
 
This prevents a language model from becoming the authority over critical business data.
 
---
 
## Event-Driven Architecture
 
n8n is used as the automation/orchestration layer for external communication. The backend does not need to contain every notification workflow itself.
 
For example:
 
```
Order Created → Backend → Webhook Event → n8n
  ├── WhatsApp
  ├── Email
  ├── Slack
  └── Other integrations
```
 
This allows communication workflows to evolve independently from core business logic.
 
---
 
## Design Principles
 
DistribuFlow follows several architectural principles:
 
- **Separation of Concerns** — AI, API, services, repositories, database, and automation have distinct responsibilities.
- **Source of Truth** — PostgreSQL remains authoritative for operational information.
- **Deterministic Business Logic** — Critical operations are handled by Python services rather than relying entirely on LLM output.
- **Human-in-the-Loop** — Managers remain responsible for operational approval.
- **Event-Driven Automation** — n8n handles external workflows and notifications.
- **Conversational Interface** — Distributors interact naturally without needing to learn a new ordering interface.
- **Extensibility** — The architecture allows future integrations such as ERP, CRM, payment gateways, logistics systems, email, Slack, and additional messaging platforms.
---
 
## Future Roadmap
 
### Completed
- [x] WhatsApp conversational order intake
- [x] LangGraph agent
- [x] Intent classification
- [x] Structured order extraction
- [x] Hindi / English / Hinglish support
- [x] PostgreSQL integration
- [x] Product catalog management
- [x] Inventory validation
- [x] Credit validation
- [x] Delivery address collection
- [x] Requested delivery date
- [x] Draft orders
- [x] Credit Hold orders
- [x] Sales approval workflow
- [x] Order cancellation
- [x] Automated PDF invoice generation
- [x] Invoice retrieval
- [x] WhatsApp invoice delivery
- [x] n8n automation
- [x] Admin dashboard
- [x] Product management
- [x] Distributor management
- [x] Order search/filtering
- [x] Admin stock management
- [x] Admin credit management
- [x] Product fuzzy matching / typo handling
### Future
- [ ] Distributor-specific pricing
- [ ] Inventory adjustment history
- [ ] Credit adjustment history
- [ ] Full authentication and role-based access control
- [ ] Admin audit logs
- [ ] Advanced analytics
- [ ] Sales forecasting
- [ ] Automatic reorder recommendations
- [ ] Delivery/logistics integration
- [ ] ERP integration
- [ ] Multi-warehouse inventory
- [ ] Multi-language expansion
- [ ] Production cloud deployment
- [ ] Automated AI evaluation pipeline
---
 
## Potential V2 Architecture
 
Future versions can introduce a dedicated pricing layer:
 
```
                 Distributor
                     │
                     ▼
              Pricing Engine
                     │
          ┌──────────┴──────────┐
          │                     │
 Standard Price        Distributor Override
          │                     │
          └──────────┬──────────┘
                      ▼
              Final Order Price
```
 
This would allow different distributors to receive negotiated prices while preserving the existing order-processing architecture.
 
---
 
## Current Project Scope
 
DistribuFlow is currently designed as an **MVP / prototype-grade** operational system demonstrating an end-to-end AI-assisted distributor ordering workflow.
 
Before production deployment, additional infrastructure should be added for:
 
- Authentication
- Authorization
- Secrets management
- HTTPS
- Production database configuration
- Audit logging
- Monitoring
- Rate limiting
- Retry mechanisms
- Queue-based background jobs
- Automated testing
- Production deployment
- Role-based access control
The current implementation intentionally prioritizes demonstrating the complete business workflow.
 
---
 
## Why DistribuFlow?
 
Traditional distributor ordering often involves:
 
```
Phone Calls
    + WhatsApp Messages
    + Manual Order Entry
    + Spreadsheet Inventory
    + Manual Credit Checking
    + Manual Approval
    + Manual Invoice Generation
```
 
DistribuFlow brings these processes into one connected workflow:
 
```
                 DISTRIBUTOR
                      │
                      ▼
                 WhatsApp
                      │
                      ▼
                Agentic AI
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Catalog      Credit      Inventory
          │           │           │
          └───────────┼───────────┘
                       ▼
                  PostgreSQL
                       │
                       ▼
               Admin Dashboard
                       │
                       ▼
                Sales Approval
                       │
                       ▼
               Invoice Engine
                       │
                       ▼
                  WhatsApp
```
 
The result is a single connected order lifecycle from conversational request to approved order and invoice delivery.
 
---
 
## Key Highlights
 
| Capability | Technology |
|---|---|
| Conversational AI | LangGraph + Llama 3.3 |
| LLM Provider | Groq |
| Backend API | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Workflow Automation | n8n |
| Messaging | WhatsApp Cloud API |
| Admin Interface | HTML / JavaScript / Tailwind |
| Voice Processing | Speech-to-Text pipeline |
| Product Resolution | Deterministic fuzzy matching |
| Invoice | Automated PDF generation |
| Notifications | n8n Webhooks |
| Development | Python / Git / Docker |
 
---
 
## License
 
MIT License
 
---
 
## Author
 
**Ayush Shukla**
- GitHub: [github.com/technospes](https://github.com/technospes)
- LinkedIn: [linkedin.com/in/ayushshukla-ar](https://www.linkedin.com/in/ayushshukla-ar/)
