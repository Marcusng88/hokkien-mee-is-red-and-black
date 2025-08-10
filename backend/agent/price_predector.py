import joblib
import pandas as pd
import os
import logging
from typing import Dict, Any, Optional, List
import numpy as np

# Set up logging
logger = logging.getLogger(__name__)

# Global model variable
_model = None
_model_loaded = False

current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "ml_model", "nft_price_model.pkl")

all_categories = [
    'Art', 'Photography', 'Music', 'Gaming', 'Sports', 'Collectibles',
    '3D Art', 'Digital Art', 'Pixel Art', 'Abstract', 'Nature', 'Portrait'
]

def load_model():
    """Load the ML model with error handling"""
    global _model, _model_loaded

    if _model_loaded:
        return _model

    try:
        if not os.path.exists(model_path):
            logger.error(f"Model file not found at {model_path}")
            return None

        _model = joblib.load(model_path)
        _model_loaded = True
        logger.info("NFT price prediction model loaded successfully")
        return _model
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None

def validate_input(title: str, description: str, category: str) -> Dict[str, Any]:
    """Validate input parameters for price prediction"""
    errors = []

    if not title or not title.strip():
        errors.append("Title is required")
    elif len(title.strip()) < 3:
        errors.append("Title must be at least 3 characters long")
    elif len(title.strip()) > 100:
        errors.append("Title must be less than 100 characters")

    if not description or not description.strip():
        errors.append("Description is required")
    elif len(description.strip()) < 10:
        errors.append("Description must be at least 10 characters long")
    elif len(description.strip()) > 1000:
        errors.append("Description must be less than 1000 characters")

    if not category or category not in all_categories:
        errors.append(f"Category must be one of: {', '.join(all_categories)}")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }

def predict_price(title: str, description: str, category: str) -> Dict[str, Any]:
    """
    Predict NFT price with enhanced error handling and confidence scoring

    Args:
        title: NFT title
        description: NFT description
        category: NFT category

    Returns:
        Dictionary containing prediction results
    """
    try:
        # Validate inputs
        validation = validate_input(title, description, category)
        if not validation["valid"]:
            return {
                "success": False,
                "error": "Invalid input",
                "details": validation["errors"],
                "predicted_price": None,
                "confidence_score": 0.0
            }

        # Load model
        model = load_model()
        if model is None:
            return {
                "success": False,
                "error": "Model not available",
                "details": ["Price prediction model could not be loaded"],
                "predicted_price": None,
                "confidence_score": 0.0
            }

        # Prepare data for prediction
        df = pd.DataFrame([{
            "Title": title.strip(),
            "Description": description.strip(),
            "Category": category
        }])

        # Make prediction
        prediction = model.predict(df)[0]
        predicted_price = round(float(prediction), 2)

        # Calculate confidence score based on various factors
        confidence_score = calculate_confidence_score(title, description, category, predicted_price)

        return {
            "success": True,
            "predicted_price": predicted_price,
            "confidence_score": confidence_score,
            "currency": "SUI",
            "factors": analyze_price_factors(title, description, category),
            "category": category,
            "error": None
        }

    except Exception as e:
        logger.error(f"Error in price prediction: {str(e)}")
        return {
            "success": False,
            "error": "Prediction failed",
            "details": [str(e)],
            "predicted_price": None,
            "confidence_score": 0.0
        }

def calculate_confidence_score(title: str, description: str, category: str, predicted_price: float) -> float:
    """Calculate confidence score for the prediction"""
    try:
        confidence = 0.7  # Base confidence

        # Adjust based on title quality
        if len(title.strip()) >= 10:
            confidence += 0.1
        if any(word in title.lower() for word in ['unique', 'rare', 'limited', 'exclusive']):
            confidence += 0.05

        # Adjust based on description quality
        if len(description.strip()) >= 50:
            confidence += 0.1
        if len(description.strip()) >= 100:
            confidence += 0.05

        # Adjust based on category popularity
        popular_categories = ['Art', 'Digital Art', 'Gaming', 'Collectibles']
        if category in popular_categories:
            confidence += 0.05

        # Adjust based on price range (more confident in typical ranges)
        if 0.1 <= predicted_price <= 100:
            confidence += 0.05
        elif predicted_price > 1000:
            confidence -= 0.1

        return min(max(confidence, 0.0), 1.0)  # Clamp between 0 and 1

    except Exception:
        return 0.7  # Default confidence

def analyze_price_factors(title: str, description: str, category: str) -> Dict[str, Any]:
    """Analyze factors that might influence the price"""
    factors = {
        "title_keywords": [],
        "description_length": len(description.strip()),
        "category_popularity": get_category_popularity(category),
        "quality_indicators": []
    }

    # Analyze title keywords that might increase value
    value_keywords = ['rare', 'unique', 'limited', 'exclusive', 'original', 'handmade', 'custom']
    factors["title_keywords"] = [word for word in value_keywords if word in title.lower()]

    # Quality indicators
    if len(description.strip()) > 100:
        factors["quality_indicators"].append("Detailed description")
    if len(title.strip()) > 15:
        factors["quality_indicators"].append("Descriptive title")
    if any(keyword in description.lower() for keyword in ['artist', 'creator', 'original']):
        factors["quality_indicators"].append("Creator mentioned")

    return factors

def get_category_popularity(category: str) -> str:
    """Get popularity rating for category"""
    high_popularity = ['Art', 'Digital Art', 'Gaming', 'Collectibles']
    medium_popularity = ['Photography', 'Music', '3D Art']

    if category in high_popularity:
        return "High"
    elif category in medium_popularity:
        return "Medium"
    else:
        return "Low"

def main():
    print("Available Categories:")
    print(", ".join(all_categories))
    
    title = input("Enter NFT title: ")
    description = input("Enter NFT description: ")
    category = input("Enter NFT category: ")
    
    if category not in all_categories:
        print("Invalid category. Please choose from the list above.")
        return
    
    predicted_price = predict_price(title, description, category)
    print(f"Predicted Price: {predicted_price} SUI")

if __name__ == "__main__":
    main()
