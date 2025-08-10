"""
Price Prediction API Router
Provides real-time NFT price prediction endpoints
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Set up logging
logger = logging.getLogger(__name__)

# Import price prediction functionality
try:
    from agent.price_predector import predict_price, all_categories
except ImportError:
    try:
        from backend.agent.price_predector import predict_price, all_categories
    except ImportError:
        logger.error("Could not import price prediction module")
        predict_price = None
        all_categories = []

router = APIRouter(prefix="/api/price", tags=["price-prediction"])

class PricePredictionRequest(BaseModel):
    """Request model for price prediction"""
    title: str = Field(..., min_length=3, max_length=100, description="NFT title")
    description: str = Field(..., min_length=10, max_length=1000, description="NFT description")
    category: str = Field(..., description="NFT category")

class PricePredictionResponse(BaseModel):
    """Response model for price prediction"""
    success: bool
    predicted_price: float | None = None
    confidence_score: float
    currency: str = "SUI"
    factors: Dict[str, Any] | None = None
    category: str | None = None
    error: str | None = None
    details: list[str] | None = None

class CategoriesResponse(BaseModel):
    """Response model for available categories"""
    categories: list[str]
    total_count: int

@router.get("/categories", response_model=CategoriesResponse)
async def get_categories():
    """Get all available NFT categories for price prediction"""
    try:
        return CategoriesResponse(
            categories=all_categories,
            total_count=len(all_categories)
        )
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get categories")

@router.post("/predict", response_model=PricePredictionResponse)
async def predict_nft_price(request: PricePredictionRequest):
    """
    Predict NFT price based on title, description, and category
    
    This endpoint uses a trained machine learning model to predict
    the suggested price for an NFT based on its metadata.
    """
    try:
        if predict_price is None:
            raise HTTPException(
                status_code=503, 
                detail="Price prediction service is not available"
            )
        
        # Validate category
        if request.category not in all_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of: {', '.join(all_categories)}"
            )
        
        # Make prediction
        result = predict_price(
            title=request.title,
            description=request.description,
            category=request.category
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Prediction failed")
            )
        
        return PricePredictionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in price prediction endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/predict-batch", response_model=list[PricePredictionResponse])
async def predict_batch_prices(requests: list[PricePredictionRequest]):
    """
    Predict prices for multiple NFTs in batch
    
    Useful for bulk price estimation or comparison
    """
    try:
        if predict_price is None:
            raise HTTPException(
                status_code=503, 
                detail="Price prediction service is not available"
            )
        
        if len(requests) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 predictions per batch request"
            )
        
        results = []
        for req in requests:
            # Validate category
            if req.category not in all_categories:
                results.append(PricePredictionResponse(
                    success=False,
                    confidence_score=0.0,
                    error="Invalid category",
                    details=[f"Category must be one of: {', '.join(all_categories)}"]
                ))
                continue
            
            # Make prediction
            result = predict_price(
                title=req.title,
                description=req.description,
                category=req.category
            )
            
            results.append(PricePredictionResponse(**result))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch price prediction: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def price_prediction_health():
    """Health check for price prediction service"""
    try:
        if predict_price is None:
            return {
                "status": "unhealthy",
                "message": "Price prediction module not available",
                "model_loaded": False
            }
        
        # Test prediction with sample data
        test_result = predict_price(
            title="Test NFT",
            description="This is a test NFT for health check purposes",
            category="Art"
        )
        
        return {
            "status": "healthy" if test_result["success"] else "degraded",
            "message": "Price prediction service is operational",
            "model_loaded": test_result["success"],
            "available_categories": len(all_categories)
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
            "model_loaded": False
        }
