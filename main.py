# farmfuzion-public-api/main.py
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, func, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, Field
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="FarmFuzion Global Marketplace API",
    description="API for bulk agricultural produce sales at cooperative and international levels",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Allow all origins for public API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup - Use separate schema to avoid conflicts
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/farmfuzion_public")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "public_marketplace")

# Create engine with schema search path
engine = create_engine(DATABASE_URL, connect_args={
    'options': f'-c search_path={SCHEMA_NAME},public'
})

# Create schema if it doesn't exist
def create_schema():
    with engine.connect() as conn:
        conn.execute(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}')
        conn.commit()

create_schema()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# API Key authentication
API_KEY = os.getenv("PUBLIC_API_KEY", "your-secret-api-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Set the schema for all tables
class SchemaBase(Base):
    __abstract__ = True
    __table_args__ = {'schema': SCHEMA_NAME}

# ============================================
# Database Models
# ============================================

class Cooperative(SchemaBase):
    __tablename__ = "cooperatives"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    registration_number = Column(String, unique=True)
    county = Column(String)
    constituency = Column(String)
    ward = Column(String)
    location = Column(String)
    description = Column(Text)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CooperativeProduct(SchemaBase):
    __tablename__ = "cooperative_products"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cooperative_id = Column(String, ForeignKey(f"{SCHEMA_NAME}.cooperatives.id"))
    product_name = Column(String, nullable=False)
    category = Column(String)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    currency = Column(String, default="KES")
    total_price = Column(Float)
    available = Column(Boolean, default=True)
    harvest_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    certification = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    images = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    cooperative = relationship("Cooperative")

class BulkOrder(SchemaBase):
    __tablename__ = "bulk_orders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cooperative_product_id = Column(String, ForeignKey(f"{SCHEMA_NAME}.cooperative_products.id"))
    buyer_name = Column(String, nullable=False)
    buyer_company = Column(String, nullable=True)
    buyer_email = Column(String, nullable=False)
    buyer_phone = Column(String, nullable=True)
    buyer_country = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    shipping_address = Column(Text, nullable=True)
    shipping_method = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("CooperativeProduct")

class Tender(SchemaBase):
    __tablename__ = "tenders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    quantity_needed = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    buyer_name = Column(String, nullable=False)
    buyer_company = Column(String, nullable=True)
    buyer_email = Column(String, nullable=False)
    buyer_phone = Column(String, nullable=True)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)

class TenderResponse(SchemaBase):
    __tablename__ = "tender_responses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tender_id = Column(String, ForeignKey(f"{SCHEMA_NAME}.tenders.id"))
    cooperative_id = Column(String, ForeignKey(f"{SCHEMA_NAME}.cooperatives.id"))
    offered_price = Column(Float, nullable=False)
    available_quantity = Column(Float, nullable=False)
    delivery_timeline = Column(Integer, nullable=False)
    message = Column(Text, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tender = relationship("Tender")
    cooperative = relationship("Cooperative")

# ============================================
# Pydantic Schemas (same as before)
# ============================================

class CooperativeProductCreate(BaseModel):
    product_name: str = Field(..., description="Name of the product")
    category: Optional[str] = Field(None, description="Product category")
    quantity: float = Field(..., description="Available quantity", gt=0)
    unit: str = Field(..., description="Unit of measurement (kg, tons, bags, pieces)")
    price_per_unit: float = Field(..., description="Price per unit", gt=0)
    currency: str = Field("KES", description="Currency code")
    available: bool = Field(True, description="Is product available")
    harvest_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    certification: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None

class CooperativeProductResponse(CooperativeProductCreate):
    id: str
    cooperative_id: str
    total_price: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class BulkOrderCreate(BaseModel):
    product_id: str
    buyer_name: str
    buyer_company: Optional[str] = None
    buyer_email: str
    buyer_phone: Optional[str] = None
    buyer_country: str
    quantity: float
    shipping_address: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None

class BulkOrderResponse(BulkOrderCreate):
    id: str
    total_amount: float
    status: str
    tracking_number: Optional[str] = None
    created_at: datetime

class TenderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    quantity_needed: float
    unit: str
    deadline: datetime
    buyer_name: str
    buyer_company: Optional[str] = None
    buyer_email: str
    buyer_phone: Optional[str] = None

class TenderResponseCreate(BaseModel):
    tender_id: str
    offered_price: float
    available_quantity: float
    delivery_timeline: int
    message: Optional[str] = None

# ============================================
# API Endpoints (same as before)
# ============================================

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "FarmFuzion Global Marketplace API", "version": "1.0.0", "schema": SCHEMA_NAME}

@app.get("/api/v1/products", response_model=List[CooperativeProductResponse], tags=["Products"])
def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    certification: Optional[str] = Query(None, description="Filter by certification"),
    search: Optional[str] = Query(None, description="Search by product name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List all available cooperative products for bulk purchase"""
    query = db.query(CooperativeProduct).filter(CooperativeProduct.available == True)
    
    if category:
        query = query.filter(CooperativeProduct.category == category)
    if min_price:
        query = query.filter(CooperativeProduct.price_per_unit >= min_price)
    if max_price:
        query = query.filter(CooperativeProduct.price_per_unit <= max_price)
    if certification:
        query = query.filter(CooperativeProduct.certification == certification)
    if search:
        query = query.filter(CooperativeProduct.product_name.ilike(f"%{search}%"))
    
    products = query.offset(offset).limit(limit).all()
    
    for product in products:
        product.total_price = product.quantity * product.price_per_unit
    
    return products

@app.get("/api/v1/products/{product_id}", response_model=CooperativeProductResponse, tags=["Products"])
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific product"""
    product = db.query(CooperativeProduct).filter(CooperativeProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.total_price = product.quantity * product.price_per_unit
    return product

@app.get("/api/v1/categories", tags=["Products"])
def list_categories(db: Session = Depends(get_db)):
    """List all available product categories"""
    categories = db.query(CooperativeProduct.category).distinct().all()
    return {"categories": [c[0] for c in categories if c[0]]}

@app.post("/api/v1/orders", response_model=BulkOrderResponse, tags=["Orders"])
def create_bulk_order(order: BulkOrderCreate, db: Session = Depends(get_db)):
    """Create a bulk purchase order"""
    product = db.query(CooperativeProduct).filter(
        CooperativeProduct.id == order.product_id,
        CooperativeProduct.available == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not available")
    
    if order.quantity > product.quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity available")
    
    total_amount = product.price_per_unit * order.quantity
    
    db_order = BulkOrder(
        id=f"BO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{order.product_id[:8]}",
        cooperative_product_id=order.product_id,
        buyer_name=order.buyer_name,
        buyer_company=order.buyer_company,
        buyer_email=order.buyer_email,
        buyer_phone=order.buyer_phone,
        buyer_country=order.buyer_country,
        quantity=order.quantity,
        total_amount=total_amount,
        shipping_address=order.shipping_address,
        shipping_method=order.shipping_method,
        notes=order.notes,
        status="pending"
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    setattr(db_order, "product_name", product.product_name)
    
    return db_order

@app.get("/api/v1/tenders/open", tags=["Tenders"])
def list_open_tenders(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all open tenders for bulk purchases"""
    query = db.query(Tender).filter(
        Tender.status == "open",
        Tender.deadline > datetime.utcnow()
    )
    
    if category:
        query = query.filter(Tender.category == category)
    
    tenders = query.order_by(Tender.deadline.asc()).all()
    return tenders

@app.post("/api/v1/tenders/{tender_id}/respond", tags=["Tenders"])
def respond_to_tender(
    tender_id: str,
    response: TenderResponseCreate,
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Submit a response to a tender (requires API key)"""
    tender = db.query(Tender).filter(
        Tender.id == tender_id,
        Tender.status == "open",
        Tender.deadline > datetime.utcnow()
    ).first()
    
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found or closed")
    
    cooperative = db.query(Cooperative).filter(Cooperative.id == response.cooperative_id).first()
    if not cooperative:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    
    db_response = TenderResponse(
        tender_id=tender_id,
        cooperative_id=response.cooperative_id,
        offered_price=response.offered_price,
        available_quantity=response.available_quantity,
        delivery_timeline=response.delivery_timeline,
        message=response.message,
        status="pending"
    )
    
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    
    return {"message": "Tender response submitted successfully", "response_id": db_response.id}

@app.get("/api/v1/stats", tags=["Stats"])
def get_marketplace_stats(db: Session = Depends(get_db)):
    """Get marketplace statistics"""
    total_products = db.query(CooperativeProduct).filter(CooperativeProduct.available == True).count()
    total_cooperatives = db.query(Cooperative).filter(Cooperative.status == "active").count()
    total_orders = db.query(BulkOrder).count()
    
    categories = db.query(CooperativeProduct.category, func.count()).group_by(CooperativeProduct.category).all()
    
    return {
        "total_products": total_products,
        "total_cooperatives": total_cooperatives,
        "total_orders": total_orders,
        "categories": [{"name": c[0], "count": c[1]} for c in categories if c[0]]
    }

# Create tables on startup
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)