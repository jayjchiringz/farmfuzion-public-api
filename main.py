# farmfuzion-public-api/main.py
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Boolean, func
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

if DATABASE_URL:
    try:
        # Create engine with schema search path
        engine = create_engine(DATABASE_URL, connect_args={
            'options': f'-c search_path={SCHEMA_NAME},public'
        })
        
        # Create schema if it doesn't exist
        with engine.connect() as conn:
            conn.execute(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}')
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
        
        print(f"✅ Database connected. Schema: {SCHEMA_NAME}")
        
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
    product_name: str
    category: Optional[str] = None
    quantity: float = 0
    unit: str = "kg"
    price_per_unit: float = 0

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
        "database_connected": bool(DATABASE_URL and DATABASE_URL != ""),
        "schema": SCHEMA_NAME if DATABASE_URL else None,
        "plan": "free"
    }

@app.get("/api/v1/health", tags=["Health"])
def api_health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1/products", tags=["Products"])
def list_products(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all available cooperative products"""
    if not DATABASE_URL or not db:
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
        
        total = query.count()
        products = query.offset(offset).limit(limit).all()
        
        return {
            "data": products,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        return {
            "data": [],
            "total": 0,
            "error": str(e),
            "message": "Database query failed"
        }

@app.post("/api/v1/products", tags=["Products"])
def create_product(
    product: ProductCreate,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Create a new product (requires API key)"""
    if not DATABASE_URL or not db:
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

@app.get("/api/v1/categories", tags=["Products"])
def list_categories(db: Session = Depends(get_db)):
    """List all available product categories"""
    if not DATABASE_URL or not db:
        return {"categories": []}
    
    try:
        categories = db.query(MarketplaceProduct.category).distinct().all()
        return {"categories": [c[0] for c in categories if c[0]]}
    except Exception:
        return {"categories": []}

@app.get("/api/v1/stats", tags=["Stats"])
def get_marketplace_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    if not DATABASE_URL or not db:
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
    except Exception:
        return {
            "total_products": 0,
            "total_cooperatives": 0,
            "total_orders": 0,
            "categories": []
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)