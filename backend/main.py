"""
Industrial Parts Product Finder - FastAPI Backend
Main application file
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import logging
from pathlib import Path
import time

# Import core modules
from backend.config import AppConfig
from backend.core.catalog_processor import CatalogProcessor, Product
from backend.core.product_search import ProductSearchEngine
from backend.core.recommender import ProductRecommender
from backend.core.query_processor import QueryProcessor, QueryResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProductFinder")

# FastAPI app
app = FastAPI(
    title="Industrial Parts Product Finder API",
    description="AI-powered product search for industrial parts catalogs",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
try:
    app.mount("/static", StaticFiles(directory="frontend"), name="static")
except:
    logger.warning("Frontend directory not found")

# Global system components
config = AppConfig()
catalog_processor = None
search_engine = None
recommender = None
query_processor = None
system_initialized = False
products_list = []

# Pydantic models
class SearchQuery(BaseModel):
    query: str
    max_results: Optional[int] = 5

class SearchResponse(BaseModel):
    response: str
    products: List[dict] = []
    recommendations: List[dict] = []
    processing_time: float
    query_type: str

class SystemStatus(BaseModel):
    initialized: bool
    products_loaded: int
    catalogs_processed: int
    recommendations_available: bool
    search_ready: bool

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    global system_initialized
    logger.info("Starting Product Finder system...")

# Routes
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve main frontend page"""
    try:
        frontend_path = Path("frontend/index.html")
        if frontend_path.exists():
            with open(frontend_path, encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse("""
                <h1>Industrial Parts Product Finder</h1>
                <p>Backend is running!</p>
                <p>Frontend not found. Please ensure frontend/index.html exists.</p>
                <p><a href="/docs">API Documentation</a></p>
            """)
    except Exception as e:
        return HTMLResponse(f"<h1>Error loading frontend: {e}</h1>")

@app.post("/api/initialize")
async def initialize_system():
    """Initialize the product finder system"""
    global catalog_processor, search_engine, recommender, query_processor
    global system_initialized, products_list, config

    try:
        logger.info("=" * 60)
        logger.info("INITIALIZING PRODUCT FINDER SYSTEM")
        logger.info("=" * 60)

        # Step 1: Process catalogs
        logger.info("\nStep 1/4: Processing catalogs...")
        catalog_processor = CatalogProcessor(config)

        catalog_processor.process_labels_catalog()
        catalog_processor.process_handling_catalog()

        products_list = catalog_processor.products
        stats = catalog_processor.get_stats()

        logger.info(f"Processed {stats['total_products']} products")
        for cat, count in stats['by_category'].items():
            logger.info(f"  - {cat}: {count} products")

        # Export products
        catalog_processor.export_products()

        # Step 2: Build search index
        logger.info("\nStep 2/4: Building search index...")
        search_engine = ProductSearchEngine(config)
        documents = catalog_processor.create_searchable_documents()

        if not search_engine.build_index(documents):
            raise Exception("Failed to build search index")

        logger.info(f"Search index ready with {len(documents)} documents")

        # Step 3: Load recommendations
        logger.info("\nStep 3/4: Loading recommendation data...")
        recommender = ProductRecommender(config)

        if recommender.load_purchase_data():
            rec_stats = recommender.get_stats()
            logger.info(f"Recommendations loaded: {rec_stats['total_products']} products with associations")
        else:
            logger.warning("Recommendations not loaded (non-critical)")

        # Step 4: Initialize query processor
        logger.info("\nStep 4/4: Initializing AI query processor...")
        query_processor = QueryProcessor(config)
        logger.info("Query processor ready")

        system_initialized = True

        logger.info("\n" + "=" * 60)
        logger.info("SYSTEM INITIALIZATION COMPLETE!")
        logger.info("=" * 60)

        return {
            "status": "success",
            "message": "System initialized successfully",
            "stats": {
                "products": len(products_list),
                "categories": len(stats['by_category']),
                "recommendations": rec_stats['total_products'] if recommender else 0
            }
        }

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Initialization failed: {str(e)}"
        }

@app.post("/api/search", response_model=SearchResponse)
async def search_products(query: SearchQuery):
    """Search for products"""
    if not system_initialized:
        raise HTTPException(
            status_code=503,
            detail="System not initialized. Please call /api/initialize first."
        )

    try:
        # Process query
        result = query_processor.process_query(
            query.query,
            search_engine,
            recommender,
            products_list
        )

        # Format products
        products_data = [
            {
                'product_id': p.product_id,
                'name': p.name,
                'reference': p.reference_number,
                'category': p.category,
                'page': p.page_number,
                'catalog': p.catalog_source,
                'description': p.description[:200]
            }
            for p in result.products
        ]

        # Format recommendations
        recommendations_data = [
            {
                'product_id': r['product'].product_id,
                'name': r['product'].name,
                'reference': r['product'].reference_number,
                'score': r['score'],
                'reason': r['reason']
            }
            for r in result.recommendations
        ]

        return SearchResponse(
            response=result.response,
            products=products_data,
            recommendations=recommendations_data,
            processing_time=result.processing_time,
            query_type=result.query_type.value
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status", response_model=SystemStatus)
async def get_status():
    """Get system status"""
    return SystemStatus(
        initialized=system_initialized,
        products_loaded=len(products_list),
        catalogs_processed=2 if catalog_processor else 0,
        recommendations_available=recommender is not None and recommender.associations,
        search_ready=search_engine is not None and search_engine.index is not None
    )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "system_initialized": system_initialized
    }

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )