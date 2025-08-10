"""
FraudGuard Backend API
FastAPI application for AI-powered fraud detection in NFT marketplace
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

# Note: These imports will work once dependencies are installed
try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    # Fallback for development without dependencies
    FastAPI = None
    HTTPException = None
    BackgroundTasks = None
    CORSMiddleware = None
    BaseModel = None
    uvicorn = None

try:
    # Try relative imports first (when running from backend directory)
    from core.config import settings,validate_ai_config
    from agent.listener import start_fraud_detection_service, stop_fraud_detection_service
    from agent.sui_client import sui_client
    from agent.supabase_client import supabase_client
    from agent.fraud_detector import analyze_nft_for_fraud, initialize_fraud_detector, NFTData
    from agent.chat_bot import get_nft_market_analysis, validate_environment
    from api.marketplace import router as marketplace_router
    from api.nft import router as nft_router
    from api.listings import router as listings_router
    from api.transactions import router as transactions_router
    from database.connection import create_tables
    from ai_reputation_agent import AIReputationAgent
except ImportError:
    # Fallback to absolute imports (when running from project root)
    from backend.core.config import settings,validate_ai_config
    from backend.agent.listener import start_fraud_detection_service, stop_fraud_detection_service
    from backend.agent.sui_client import sui_client
    from backend.agent.supabase_client import supabase_client
    from backend.agent.fraud_detector import analyze_nft_for_fraud, initialize_fraud_detector, NFTData
    from backend.agent.chat_bot import get_nft_market_analysis, validate_environment
    from backend.api.marketplace import router as marketplace_router
    from backend.api.nft import router as nft_router
    from backend.api.listings import router as listings_router
    from backend.api.transactions import router as transactions_router
    from backend.database.connection import create_tables
    from backend.ai_reputation_agent import AIReputationAgent

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Health check response model
class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    sui_connected: bool
    ai_configured: bool
    fraud_detection_active: bool
    listing_sync_active: bool
    ai_reputation_active: bool


# Chat bot models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str


class ChatResponse(BaseModel):
    """Chat response model"""
    query: str
    summary: str
    images: List[str]
    success: bool
    error: Optional[str] = None


# Background tasks
fraud_detection_task = None
listing_sync_task = None
ai_reputation_task = None
ai_reputation_agent = None


@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager"""
    global fraud_detection_task, ai_reputation_task, ai_reputation_agent

    logger.info("Starting FraudGuard backend...")

    # Create database tables
    create_tables()

    # Initialize Supabase client
    logger.info("Initializing Supabase client...")
    await supabase_client.initialize()
    
    # Initialize Unified Fraud Detection System
    logger.info("Initializing unified fraud detection system...")
    try:
        if await initialize_fraud_detector():
            logger.info("Unified fraud detection system initialized successfully")
        else:
            logger.warning("Fraud detection system initialization failed - using fallback analysis")
    except Exception as e:
        logger.error(f"Error initializing fraud detection system: {e}")
        logger.warning("Will use fallback fraud detection")

    # Validate configuration
    if not validate_ai_config():
        logger.warning("AI configuration incomplete - analysis may not be available")

    # Initialize AI Reputation Agent
    logger.info("🤖 Initializing AI Reputation Agent...")
    try:
        ai_reputation_agent = AIReputationAgent()
        logger.info("AI Reputation Agent initialized successfully")
        
        # Start AI reputation monitoring in background
        logger.info("🔄 Starting AI Reputation Monitoring...")
        ai_reputation_task = asyncio.create_task(ai_reputation_agent.start_monitoring())
        logger.info("AI Reputation Agent monitoring started")
        
    except Exception as e:
        logger.error(f"Error initializing AI Reputation Agent: {e}")
        logger.warning("AI Reputation Agent will not be available")

    # Start fraud detection service in background
    fraud_detection_task = asyncio.create_task(start_fraud_detection_service())
    yield

    # Cleanup
    logger.info("Shutting down FraudGuard backend...")
    
    # Stop AI Reputation Agent
    if ai_reputation_agent:
        logger.info("🛑 Stopping AI Reputation Agent...")
        ai_reputation_agent.stop_monitoring()
        
    if ai_reputation_task:
        ai_reputation_task.cancel()
        try:
            await ai_reputation_task
        except asyncio.CancelledError:
            logger.info("AI Reputation Agent task cancelled")
    
    if fraud_detection_task:
        fraud_detection_task.cancel()
    if listing_sync_task:
        listing_sync_task.cancel()
    await stop_fraud_detection_service()

# Create FastAPI app
if FastAPI:
    app = FastAPI(
        title="FraudGuard API",
        description="AI-powered fraud detection for NFT marketplace",
        version="1.0.0",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routes
    app.include_router(marketplace_router)
    app.include_router(nft_router)
    app.include_router(listings_router)
    app.include_router(transactions_router)
    
else:
    app = None
    logger.warning("FastAPI not available - API will not be available")


# API Routes
if app:
    @app.get("/", response_model=Dict)
    async def root():
        """Root endpoint"""
        return {
            "message": "FraudGuard API",
            "version": "1.0.0",
            "status": "running"
        }

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        try:
            # Check Sui connection (interface only)
            sui_connected = await sui_client.initialize() if sui_client else False

            return HealthResponse(
                status="healthy",
                version="1.0.0",
                sui_connected=sui_connected,
                ai_configured=validate_ai_config(),
                fraud_detection_active=fraud_detection_task is not None and not fraud_detection_task.done(),
                listing_sync_active=listing_sync_task is not None and not listing_sync_task.done(),
                ai_reputation_active=ai_reputation_task is not None and not ai_reputation_task.done()
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail="Health check failed")

    @app.get("/health/ai-reputation")
    async def check_ai_reputation_health():
        """Check AI Reputation Agent health"""
        global ai_reputation_agent
        
        if ai_reputation_agent and ai_reputation_agent.is_running:
            return {
                "status": "healthy",
                "ai_reputation_running": True,
                "last_processed_nft": str(ai_reputation_agent.last_processed_nft) if ai_reputation_agent.last_processed_nft else None,
                "message": "AI Reputation Agent is actively monitoring"
            }
        else:
            return {
                "status": "unhealthy", 
                "ai_reputation_running": False,
                "message": "AI Reputation Agent is not running"
            }

    @app.post("/admin/trigger-ai-reputation-analysis")
    async def trigger_ai_reputation_analysis():
        """Manually trigger AI reputation analysis for testing"""
        global ai_reputation_agent
        
        if not ai_reputation_agent:
            raise HTTPException(status_code=503, detail="AI Reputation Agent not initialized")
        
        try:
            db = ai_reputation_agent.get_db_session()
            new_nfts = ai_reputation_agent.get_new_nfts_since_last_check(db)
            
            if not new_nfts:
                return {"message": "No new NFTs found for reputation analysis", "processed": 0}
            
            processed_count = 0
            for nft in new_nfts:
                success = await ai_reputation_agent.process_nft_with_ai(db, nft)
                if success:
                    processed_count += 1
            
            db.close()
            
            return {
                "message": f"AI reputation analysis triggered successfully",
                "total_nfts": len(new_nfts),
                "processed": processed_count
            }
            
        except Exception as e:
            logger.error(f"Error triggering AI reputation analysis: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to trigger AI reputation analysis: {str(e)}")

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat_with_bot(request: ChatRequest):
        """Chat with the NFT market analysis bot"""
        try:
            # Validate environment first
            is_valid, error_msg = validate_environment()
            if not is_valid:
                logger.warning(f"Chat bot environment validation failed: {error_msg}")
                return ChatResponse(
                    query=request.message,
                    summary="I'm sorry, but I'm currently unable to provide market analysis due to configuration issues. Please try again later.",
                    images=[],
                    success=False,
                    error=error_msg
                )

            # Get market analysis
            result = get_nft_market_analysis(request.message)

            return ChatResponse(
                query=result["query"],
                summary=result["summary"],
                images=result["images"],
                success=True
            )
        except Exception as e:
            logger.error(f"Chat bot error: {e}")
            return ChatResponse(
                query=request.message,
                summary="I'm sorry, but I encountered an error while processing your request. Please try again later.",
                images=[],
                success=False,
                error=str(e)
            )


# Development server
if __name__ == "__main__":
    if uvicorn and app:
        uvicorn.run(
            "main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level=settings.log_level.lower()
        )
    else:
        logger.error("FastAPI dependencies not available")
        print("Please install dependencies: pip install -r requirements.txt")