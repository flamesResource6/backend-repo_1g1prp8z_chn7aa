import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from database import db, create_document, get_documents
from schemas import Product as ProductSchema, Order as OrderSchema, OrderItem as OrderItemSchema

app = FastAPI(title="UMKM Food Commerce API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "UMKM Food Commerce API is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set")
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---------- Schemas for requests ----------
class CreateOrderItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1)

class CreateOrderRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[CreateOrderItem]
    notes: Optional[str] = None


# ---------- Seed sample products if empty ----------
def seed_products_if_empty() -> None:
    if db is None:
        return
    count = db["product"].count_documents({})
    if count > 0:
        return
    sample_products: List[Dict[str, Any]] = [
        {
            "name": "Strawberry Bubble Tea",
            "description": "Refreshing strawberry milk tea with chewy tapioca pearls.",
            "price": 18000,
            "category": "Drinks",
            "image": "https://images.unsplash.com/photo-1613478223719-2ab802602423?q=80&w=1200&auto=format&fit=crop",
            "vendor": "Boba Bliss UMKM",
            "rating": 4.7,
            "tags": ["boba", "strawberry", "sweet"],
            "in_stock": True,
        },
        {
            "name": "Classic Milk Tea",
            "description": "Smooth black tea with creamy milk and brown sugar pearls.",
            "price": 16000,
            "category": "Drinks",
            "image": "https://images.unsplash.com/photo-1592861956120-e524fc739696?q=80&w=1200&auto=format&fit=crop",
            "vendor": "Kopi & Teh Lokal",
            "rating": 4.6,
            "tags": ["boba", "milk tea"],
            "in_stock": True,
        },
        {
            "name": "Spicy Chicken Skewers",
            "description": "Grilled chicken satay with homemade spicy sauce.",
            "price": 22000,
            "category": "Snacks",
            "image": "https://images.unsplash.com/photo-1666001085700-0610a7f0b11d?q=80&w=1200&auto=format&fit=crop",
            "vendor": "Satay UMKM",
            "rating": 4.4,
            "tags": ["spicy", "protein"],
            "in_stock": True,
        },
        {
            "name": "Chocolate Banana Crepes",
            "description": "Soft crepes filled with banana and chocolate drizzle.",
            "price": 15000,
            "category": "Dessert",
            "image": "https://images.unsplash.com/photo-1541599188778-cdc73298e8f8?q=80&w=1200&auto=format&fit=crop",
            "vendor": "Manis Lokal",
            "rating": 4.8,
            "tags": ["dessert", "sweet"],
            "in_stock": True,
        },
    ]
    db["product"].insert_many(sample_products)


@app.get("/api/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    if db is None:
        # Fallback to static list if db isn't configured
        fallback = [
            {"name": "Sample Bubble Tea", "description": "Example product", "price": 15000, "category": "Drinks", "image": None, "vendor": "UMKM Sample", "rating": 4.5, "tags": ["sample"], "in_stock": True}
        ]
        return {"items": fallback}

    seed_products_if_empty()

    filter_dict: Dict[str, Any] = {}
    if category:
        filter_dict["category"] = category
    if q:
        filter_dict["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]

    items = list(db["product"].find(filter_dict))
    for it in items:
        it["_id"] = str(it["_id"])  # Serialize ObjectId
    return {"items": items}


@app.get("/api/categories")
def list_categories():
    if db is None:
        return {"categories": ["Drinks", "Snacks", "Dessert"]}
    seed_products_if_empty()
    cats = db["product"].distinct("category")
    return {"categories": cats}


@app.post("/api/orders")
def create_order(payload: CreateOrderRequest):
    # Build order items snapshot with current product data
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items provided")

    order_items: List[OrderItemSchema] = []
    subtotal = 0.0

    for line in payload.items:
        # Find product
        prod = None
        if db is not None:
            prod = db["product"].find_one({"_id": __import__('bson').ObjectId(line.product_id)}) if line.product_id else None
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product not found: {line.product_id}")
        name = prod.get("name")
        price = float(prod.get("price", 0))
        quantity = int(line.quantity)
        subtotal += price * quantity
        order_items.append(OrderItemSchema(product_id=str(prod.get("_id")), name=name, price=price, quantity=quantity))

    order_doc = OrderSchema(
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_address=payload.customer_address,
        items=order_items,
        subtotal=round(subtotal, 2),
        notes=payload.notes,
    )

    try:
        order_id = create_document("order", order_doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

    return {"message": "Order created", "order_id": order_id}


@app.get("/schema")
def get_schema_definitions():
    """Expose Pydantic schema models for tooling."""
    return {
        "product": ProductSchema.model_json_schema(),
        "order": OrderSchema.model_json_schema(),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
