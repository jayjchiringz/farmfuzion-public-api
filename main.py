# farmfuzion-public-api/main.py
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import os
import uuid

app = FastAPI(
    title="FarmFuzion Global Marketplace API",
    description="API for bulk agricultural produce sales",
    version="1.0.0"
)

# CORS - Allow all for now (restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Database Setup - Graceful handling
# ============================================
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "public_marketplace")

# Database session placeholder
db_session = None
engine = None
SessionLocal = None
Base = None
MarketplaceProduct = None

if DATABASE_URL:
    try:
        # Create engine with schema search path
        engine = create_engine(DATABASE_URL, connect_args={
            'options': f'-c search_path={SCHEMA_NAME},public'
        })
        
        # Create schema if it doesn't exist - FIX: Use text() wrapper
        with engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}'))
            conn.commit()
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()
        
        # Simple model for testing
        class MarketplaceProduct(Base):
            __tablename__ = "marketplace_products"
            __table_args__ = {'schema': SCHEMA_NAME}
            id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
            product_name = Column(String, nullable=False)
            category = Column(String)
            quantity = Column(Float, default=0)
            unit = Column(String, default="kg")
            price_per_unit = Column(Float, default=0)
            available = Column(Boolean, default=True)
            created_at = Column(DateTime, default=datetime.utcnow)
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        print(f"✅ Database connected successfully. Schema: {SCHEMA_NAME}")
        
    except Exception as e:
        print(f"⚠️ Database connection error: {e}")
        def get_db():
            yield None
else:
    print("⚠️ DATABASE_URL not set - running without database")
    def get_db():
        yield None

# ============================================
# API Key Authentication (Optional)
# ============================================
API_KEY = os.getenv("PUBLIC_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if API_KEY and api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# ============================================
# Pydantic Schemas
# ============================================
class ProductCreate(BaseModel):
    product_name: str = Field(..., description="Name of the product")
    category: Optional[str] = Field(None, description="Product category")
    quantity: float = Field(0, description="Available quantity", ge=0)
    unit: str = Field("kg", description="Unit of measurement")
    price_per_unit: float = Field(0, description="Price per unit", ge=0)

class ProductResponse(ProductCreate):
    id: str
    available: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================
# API Endpoints
# ============================================

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "FarmFuzion Global Marketplace API",
        "version": "1.0.0",
        "database_connected": bool(DATABASE_URL and engine is not None),
        "schema": SCHEMA_NAME if DATABASE_URL else None,
        "plan": "free"
    }

@app.get("/api/v1/health", tags=["Health"])
def api_health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1/products", tags=["Products"])
def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    search: Optional[str] = Query(None, description="Search by product name"),
    sort: str = Query("newest", description="Sort order: newest, price_asc, price_desc"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """List all available cooperative products"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        return {
            "data": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "Database not configured - running in demo mode"
        }
    
    try:
        query = db.query(MarketplaceProduct).filter(MarketplaceProduct.available == True)
        
        if category:
            query = query.filter(MarketplaceProduct.category == category)
        if min_price:
            query = query.filter(MarketplaceProduct.price_per_unit >= min_price)
        if max_price:
            query = query.filter(MarketplaceProduct.price_per_unit <= max_price)
        if search:
            query = query.filter(MarketplaceProduct.product_name.ilike(f"%{search}%"))
        
        # Apply sorting
        if sort == "price_asc":
            query = query.order_by(MarketplaceProduct.price_per_unit.asc())
        elif sort == "price_desc":
            query = query.order_by(MarketplaceProduct.price_per_unit.desc())
        else:  # newest
            query = query.order_by(MarketplaceProduct.created_at.desc())
        
        total = query.count()
        products = query.offset(offset).limit(limit).all()
        
        # Convert SQLAlchemy objects to dictionaries (this is the key fix!)
        products_data = []
        for p in products:
            products_data.append({
                "id": p.id,
                "product_name": p.product_name,
                "category": p.category,
                "quantity": p.quantity,
                "unit": p.unit,
                "price_per_unit": p.price_per_unit,
                "currency": "KES",
                "total_price": p.quantity * p.price_per_unit,
                "available": p.available,
                "certification": None,
                "description": None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "cooperative_name": None,
                "source_farmer_name": None
            })
        
        return {
            "data": products_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        print(f"Error in list_products: {e}")
        return {
            "data": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e),
            "message": "Database query failed"
        }

@app.post("/api/v1/products", response_model=ProductResponse, tags=["Products"])
def create_product(
    product: ProductCreate,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Create a new product (requires API key)"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    try:
        db_product = MarketplaceProduct(
            product_name=product.product_name,
            category=product.category,
            quantity=product.quantity,
            unit=product.unit,
            price_per_unit=product.price_per_unit,
            available=True
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/products/{product_id}", tags=["Products"])
def get_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific product by ID"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Convert SQLAlchemy object to dictionary
    return {
        "id": product.id,
        "product_name": product.product_name,
        "category": product.category,
        "quantity": product.quantity,
        "unit": product.unit,
        "price_per_unit": product.price_per_unit,
        "currency": "KES",
        "total_price": product.quantity * product.price_per_unit,
        "available": product.available,
        "certification": None,
        "description": None,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "cooperative_name": None,
        "source_farmer_name": None
    }

@app.patch("/api/v1/products/{product_id}", tags=["Products"])
def update_product(
    product_id: str,
    updates: dict,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Update a product (requires API key)"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        for key, value in updates.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        db.commit()
        db.refresh(product)
        
        return product
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/products/{product_id}", tags=["Products"])
def delete_product(
    product_id: str,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Delete a product (requires API key)"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    product = db.query(MarketplaceProduct).filter(MarketplaceProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        db.delete(product)
        db.commit()
        return {"message": "Product deleted successfully", "id": product_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/categories", tags=["Products"])
def list_categories(db: Session = Depends(get_db)):
    """List all available product categories"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        return {"categories": []}
    
    try:
        categories = db.query(MarketplaceProduct.category).distinct().all()
        return {"categories": [c[0] for c in categories if c[0]]}
    except Exception:
        return {"categories": []}

@app.get("/api/v1/stats", tags=["Stats"])
def get_marketplace_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    if not DATABASE_URL or not db or MarketplaceProduct is None:
        return {
            "total_products": 0,
            "total_cooperatives": 0,
            "total_orders": 0,
            "categories": []
        }
    
    try:
        total_products = db.query(MarketplaceProduct).filter(MarketplaceProduct.available == True).count()
        categories = db.query(MarketplaceProduct.category, func.count()).group_by(MarketplaceProduct.category).all()
        
        return {
            "total_products": total_products,
            "total_cooperatives": 0,
            "total_orders": 0,
            "categories": [{"name": c[0], "count": c[1]} for c in categories if c[0]]
        }
    except Exception as e:
        return {
            "total_products": 0,
            "total_cooperatives": 0,
            "total_orders": 0,
            "categories": [],
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)