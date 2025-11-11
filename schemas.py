"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    phone: Optional[str] = Field(None, description="Phone number")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema for food & beverage UMKM
    Collection name: "product" (lowercase of class name)
    """
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in local currency")
    category: str = Field(..., description="Product category (e.g., Drinks, Snacks)")
    image: Optional[str] = Field(None, description="Image URL")
    vendor: Optional[str] = Field(None, description="UMKM vendor/brand name")
    rating: Optional[float] = Field(4.5, ge=0, le=5, description="Average rating")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for filtering")
    in_stock: bool = Field(True, description="Whether product is in stock")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Referenced product id as string")
    name: str = Field(..., description="Snapshot of product name")
    price: float = Field(..., ge=0, description="Snapshot of product price")
    quantity: int = Field(..., ge=1, description="Quantity ordered")

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    customer_address: Optional[str] = Field(None, description="Delivery address")
    items: List[OrderItem] = Field(..., description="Line items")
    subtotal: float = Field(..., ge=0, description="Subtotal amount")
    notes: Optional[str] = Field(None, description="Additional notes")
