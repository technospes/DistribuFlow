from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import products, distributors, orders, webhook, chat, admin

app = FastAPI(
    title="AI-DOMS API",
    description="Backend for the AI Distributor Order Management System",
    version="1.0"
)

# Enable CORS for the frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for local HTML file testing)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def health_check():
    return {"status": "AI-DOMS Backend is live and running!"}

# Register our API routers
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(distributors.router, prefix="/api/distributors", tags=["Distributors"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(chat.router, prefix="/api/chat", tags=["Internal Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Operations"])
app.include_router(webhook.router, prefix="/webhook", tags=["WhatsApp Webhook"])