"""
AI-Powered Reputation Agent with LangChain
Intelligently analyzes NFT events using Google AI to determine reputation impact
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Import database models and config
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.database import Base, User, NFT, UserReputationEvent
    from core.config import settings
    from database.connection import engine, SessionLocal
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the backend directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReputationAnalysis(BaseModel):
    """Structured output for AI reputation analysis"""
    event_sentiment: str = Field(description="Either 'positive' or 'negative'")
    severity_score: int = Field(description="Severity from 1-10 (1=minor, 10=severe)")
    confidence: float = Field(description="AI confidence level 0.0-1.0")
    reasoning: str = Field(description="Detailed explanation of the analysis")
    suggested_action: str = Field(description="Recommended action (reward/penalty/ban)")

class AIReputationAgent:
    """
    AI-powered reputation agent that uses LangChain + Google AI
    to intelligently analyze NFT events and determine reputation impact
    """
    
    def __init__(self):
        """Initialize the AI reputation agent"""
        # Use the existing database connection from database.connection
        self.engine = engine
        self.SessionLocal = SessionLocal
        
        if not self.engine or not self.SessionLocal:
            raise Exception("Database connection not available - cannot initialize AI Reputation Agent")
        
        # Initialize LangChain with Google AI
        self.llm = ChatGoogleGenerativeAI(
            model=settings.google_model,
            google_api_key=settings.google_api_key,
            temperature=0.1,
            max_tokens=1000
        )
        
        # Setup output parser
        self.parser = PydanticOutputParser(pydantic_object=ReputationAnalysis)
        
        # Create the analysis prompt
        self.analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("human", self._get_human_prompt())
        ])
        
        # Create the analysis chain
        self.analysis_chain = self.analysis_prompt | self.llm | self.parser
        
        self.last_processed_nft = None
        self.is_running = False
        
        logger.info("AI Reputation Agent initialized with Google AI")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for AI analysis"""
        return """You are an expert AI fraud detection specialist for an NFT marketplace called FraudGuard. 
        Your job is to analyze NFT creation events and determine their impact on user reputation.

        **Your Analysis Framework:**
        
        **POSITIVE EVENTS (Reward User):**
        - High-quality, original artwork
        - Authentic content with no plagiarism
        - Proper metadata and descriptions
        - Reasonable pricing
        - Creative and valuable contributions
        
        **NEGATIVE EVENTS (Penalize User):**
        - Fraudulent or fake NFTs
        - Plagiarized/stolen content
        - Spam or low-effort content
        - Misleading metadata
        - Price manipulation attempts
        - Suspicious trading patterns
        
        **SEVERITY SCORING (1-10):**
        - 1-3: Minor issues (small adjustments)
        - 4-6: Moderate concerns (standard penalties/rewards)
        - 7-8: Serious violations (significant impact)
        - 9-10: Severe fraud (potential ban consideration)
        
        **ACTIONS:**
        - reward: Add reputation points
        - penalty: Deduct reputation points  
        - ban: User should be banned (for severe cases)
        
        Always provide clear reasoning for your analysis."""
    
    def _get_human_prompt(self) -> str:
        """Get the human prompt template"""
        return """Analyze this NFT creation event for reputation impact:

        **NFT Details:**
        Title: {title}
        Description: {description}
        Creator: {creator_wallet}
        Price: {price}
        Category: {category}
        
        **AI Analysis Results:**
        Fraud Score: {fraud_score} (0.0 = authentic, 1.0 = fraudulent)
        Authenticity Score: {authenticity_score} (0.0 = fake, 1.0 = authentic)
        Plagiarism Detected: {plagiarism_detected}
        Quality Indicators: {quality_indicators}
        AI Confidence: {ai_confidence}
        
        **Additional Context:**
        Suspicious Patterns: {suspicious_patterns}
        
        {format_instructions}
        
        Provide your analysis in the exact JSON format specified."""
    
    def get_db_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    async def analyze_nft_with_ai(self, nft_record: NFT) -> ReputationAnalysis:
        """
        Use AI to analyze NFT and determine reputation impact
        
        Args:
            nft_record: NFT database record with analysis details
            
        Returns:
            ReputationAnalysis: Structured AI analysis result
        """
        try:
            # Extract analysis details
            analysis_details = nft_record.analysis_details or {}
            
            # Prepare data for AI analysis
            nft_data = {
                "title": nft_record.title or "Untitled",
                "description": nft_record.description or "No description",
                "creator_wallet": nft_record.creator_wallet_address,
                "price": float(nft_record.initial_price or 0),
                "category": nft_record.category or "Unknown",
                "fraud_score": analysis_details.get("fraud_score", 0.0),
                "authenticity_score": analysis_details.get("authenticity_score", 0.5),
                "plagiarism_detected": analysis_details.get("plagiarism_detected", False),
                "quality_indicators": analysis_details.get("quality_indicators", {}),
                "ai_confidence": analysis_details.get("ai_confidence", 0.0),
                "suspicious_patterns": analysis_details.get("suspicious_patterns", []),
                "format_instructions": self.parser.get_format_instructions()
            }
            
            logger.info(f"Sending NFT {nft_record.id} to AI for analysis...")
            
            # Get AI analysis
            result = await self.analysis_chain.ainvoke(nft_data)
            
            logger.info(f"AI Analysis Result: {result.event_sentiment} (severity: {result.severity_score})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            # Fallback analysis
            return self._fallback_analysis(nft_record)
    
    def _fallback_analysis(self, nft_record: NFT) -> ReputationAnalysis:
        """Fallback analysis when AI fails - provides varied scores based on available data"""
        analysis_details = nft_record.analysis_details or {}
        fraud_score = analysis_details.get("fraud_score", 0.0)
        authenticity_score = analysis_details.get("authenticity_score", 0.5)
        
        # Calculate severity based on fraud indicators
        if fraud_score > 0.8:
            severity = 9  # Very high fraud
            sentiment = "negative"
            confidence = 0.85
            reasoning = "Very high fraud score detected (fallback analysis)"
        elif fraud_score > 0.6:
            severity = 7  # High fraud
            sentiment = "negative"
            confidence = 0.75
            reasoning = "High fraud score detected (fallback analysis)"
        elif fraud_score > 0.4:
            severity = 5  # Moderate fraud
            sentiment = "negative"
            confidence = 0.65
            reasoning = "Moderate fraud indicators detected (fallback analysis)"
        elif authenticity_score > 0.7:
            severity = int(authenticity_score * 10)  # Scale authenticity to severity
            sentiment = "positive"
            confidence = 0.7
            reasoning = "Good authenticity score detected (fallback analysis)"
        else:
            severity = 3  # Neutral/low quality
            sentiment = "positive"
            confidence = 0.5
            reasoning = "No strong fraud indicators (fallback analysis)"
        
        return ReputationAnalysis(
            event_sentiment=sentiment,
            severity_score=severity,
            confidence=confidence,
            reasoning=reasoning,
            suggested_action="penalty" if sentiment == "negative" else "reward"
        )
    
    def calculate_reputation_change(self, ai_analysis: ReputationAnalysis) -> Tuple[int, str]:
        """
        Calculate reputation change based on AI analysis
        
        Args:
            ai_analysis: AI analysis result
            
        Returns:
            Tuple of (points_change, reason)
        """
        severity = ai_analysis.severity_score
        sentiment = ai_analysis.event_sentiment
        confidence = ai_analysis.confidence
        
        if sentiment == "negative":
            # Negative events: Variable points based on severity (1-10) and confidence
            # Base penalty: 1-10 points, scaled by confidence
            base_penalty = severity  # Direct mapping of severity to points
            confidence_multiplier = max(0.5, confidence)  # Minimum 50% confidence
            points_change = -int(base_penalty * confidence_multiplier)
            points_change = max(-15, min(-1, points_change))  # Cap between -1 and -15
            reason = f"AI detected negative event (severity {severity}, confidence {confidence:.2f}): {ai_analysis.reasoning}"
        else:
            # Positive events: Variable points based on quality and confidence
            # Base reward: 1-10 points, scaled by confidence
            base_reward = severity  # Direct mapping of severity (quality) to points
            confidence_multiplier = max(0.5, confidence)  # Minimum 50% confidence
            points_change = int(base_reward * confidence_multiplier)
            points_change = max(1, min(15, points_change))  # Cap between 1 and 15
            reason = f"AI detected positive event (quality {severity}, confidence {confidence:.2f}): {ai_analysis.reasoning}"
        
        return points_change, reason
    
    def determine_event_type(self, ai_analysis: ReputationAnalysis) -> str:
        """Determine event type from AI analysis"""
        if ai_analysis.event_sentiment == "negative":
            return "fraud_detected"
        else:
            return "positive_review"
    
    async def update_user_reputation_and_status(self, db: Session, user_id: str, 
                                               points_change: int, ai_analysis: ReputationAnalysis) -> bool:
        """
        Update user reputation score based on the points_change from reputation event
        
        Args:
            db: Database session
            user_id: User ID
            points_change: Points to add/subtract from current reputation
            ai_analysis: AI analysis result
            
        Returns:
            True if successful
        """
        try:
            user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Get current reputation score (ensure it's a float, default to 100 if None)
            current_score = float(user.reputation_score or 100.00)
            
            # Calculate new reputation score by adding the points_change
            new_score = current_score + points_change
            
            # Ensure reputation stays within bounds (0 to 100)
            new_score = max(0.0, min(100.0, new_score))
            
            # Update user record
            user.reputation_score = new_score
            user.updated_at = datetime.utcnow()
            
            logger.info(f"💯 Reputation Update for User {user_id}:")
            logger.info(f"   Previous Score: {current_score}")
            logger.info(f"   Points Change: {points_change}")
            logger.info(f"   New Score: {new_score}")
            logger.info(f"   Wallet: {user.wallet_address}")
            
            # Check if user should be banned (reputation below 50)
            if new_score < 50.0:
                # Check if user has ban-related fields (they might not exist in current schema)
                if hasattr(user, 'is_banned') and not getattr(user, 'is_banned', False):
                    setattr(user, 'is_banned', True)
                    if hasattr(user, 'ban_reason'):
                        setattr(user, 'ban_reason', f"Reputation score fell below threshold (current: {new_score})")
                    if hasattr(user, 'banned_at'):
                        setattr(user, 'banned_at', datetime.utcnow())
                    logger.warning(f"🚫 User {user_id} banned: reputation below 50 (current: {new_score})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating user reputation: {e}")
            return False
    
    async def create_reputation_event(self, db: Session, user_id: str, nft_id: str,
                                    points_change: int, reason: str, event_type: str) -> bool:
        """Create reputation event record"""
        try:
            reputation_event = UserReputationEvent(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id) if user_id else None,
                event_type=event_type,
                nft_id=uuid.UUID(nft_id) if nft_id else None,
                points_change=points_change,
                reason=reason,
                created_at=datetime.utcnow()
            )
            
            db.add(reputation_event)
            logger.info(f"Created reputation event: {event_type}, points: {points_change}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating reputation event: {e}")
            return False
    
    def resolve_user_by_wallet(self, db: Session, wallet_address: str) -> Optional[str]:
        """Resolve user ID from wallet address"""
        try:
            user = db.query(User).filter(User.wallet_address == wallet_address).first()
            return str(user.id) if user else None
        except Exception as e:
            logger.error(f"Error resolving user by wallet {wallet_address}: {e}")
            return None
    
    def ensure_user_exists(self, db: Session, wallet_address: str) -> Optional[str]:
        """Ensure user exists, create if missing"""
        try:
            user_id = self.resolve_user_by_wallet(db, wallet_address)
            if user_id:
                return user_id
            
            # Create new user with default reputation score of 100
            new_user = User(
                id=uuid.uuid4(),
                wallet_address=wallet_address,
                reputation_score=100.00,  # Set default reputation to 100
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_user)
            db.flush()  # Flush to get the ID, but don't commit yet
            
            logger.info(f"Created new user for wallet: {wallet_address} with reputation score 100")
            return str(new_user.id)
            
        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}")
            return None
    
    async def process_nft_with_ai(self, db: Session, nft_record: NFT) -> bool:
        """
        Process NFT using AI analysis for reputation scoring
        
        Args:
            db: Database session
            nft_record: NFT record to process
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"🤖 Processing NFT {nft_record.id} with AI analysis...")
            
            # 1. Ensure user exists
            user_id = self.ensure_user_exists(db, nft_record.creator_wallet_address)
            if not user_id:
                logger.error("Failed to resolve user")
                return False
            
            # 2. Get AI analysis
            ai_analysis = await self.analyze_nft_with_ai(nft_record)
            
            # 3. Calculate reputation change
            points_change, reason = self.calculate_reputation_change(ai_analysis)
            event_type = self.determine_event_type(ai_analysis)
            
            logger.info(f"🎯 AI Analysis Summary:")
            logger.info(f"   Sentiment: {ai_analysis.event_sentiment}")
            logger.info(f"   Severity: {ai_analysis.severity_score}")
            logger.info(f"   Confidence: {ai_analysis.confidence}")
            logger.info(f"   Points Change: {points_change}")
            logger.info(f"   Event Type: {event_type}")
            
            # 4. Create reputation event
            event_created = await self.create_reputation_event(
                db=db,
                user_id=user_id,
                nft_id=str(nft_record.id),
                points_change=points_change,
                reason=reason,
                event_type=event_type
            )
            
            # 5. Update user reputation and ban status
            if event_created:
                reputation_updated = await self.update_user_reputation_and_status(
                    db=db,
                    user_id=user_id,
                    points_change=points_change,
                    ai_analysis=ai_analysis
                )
                
                if reputation_updated:
                    db.commit()
                    logger.info(f"✅ Successfully processed NFT with AI: {points_change} points")
                    logger.info(f"AI Analysis: {ai_analysis.event_sentiment} (confidence: {ai_analysis.confidence})")
                    return True
                else:
                    db.rollback()
                    return False
            else:
                db.rollback()
                return False
            
        except Exception as e:
            logger.error(f"Error processing NFT with AI: {e}")
            db.rollback()
            return False
    
    def get_new_nfts_since_last_check(self, db: Session) -> List[NFT]:
        """Get NFTs created since last check"""
        try:
            query = db.query(NFT).filter(
                NFT.analysis_details.isnot(None)
            )
            
            if self.last_processed_nft:
                query = query.filter(NFT.created_at > self.last_processed_nft)
            
            nfts = query.order_by(NFT.created_at.asc()).all()
            
            if nfts:
                self.last_processed_nft = nfts[-1].created_at
                
            return nfts
            
        except Exception as e:
            logger.error(f"Error getting new NFTs: {e}")
            return []
    
    async def start_monitoring(self):
        """Start AI-powered reputation monitoring"""
        logger.info("🚀 Starting AI-Powered Reputation Monitoring")
        self.is_running = True
        
        while self.is_running:
            db = None
            try:
                db = self.get_db_session()
                
                new_nfts = self.get_new_nfts_since_last_check(db)
                
                if new_nfts:
                    logger.info(f"🤖 Processing {len(new_nfts)} NFTs with AI analysis")
                    
                    for nft in new_nfts:
                        await self.process_nft_with_ai(db, nft)
                else:
                    logger.debug("No new NFTs found for AI analysis")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in AI monitoring loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
            finally:
                if db:
                    db.close()
                    logger.debug("Database connection closed")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        logger.info("🛑 Stopping AI Reputation Monitoring")
        self.is_running = False


# Standalone execution (optional - usually run via start.py)
if __name__ == "__main__":
    async def main():
        agent = AIReputationAgent()
        await agent.start_monitoring()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("AI Reputation Agent stopped by user")
    except Exception as e:
        logger.error(f"AI Reputation Agent crashed: {e}")
