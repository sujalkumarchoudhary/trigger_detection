"""
Sentiment Analyzer for trigger detection
Uses TextBlob for basic sentiment analysis
"""
from typing import Dict, Tuple
import re

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


class SentimentAnalyzer:
    """
    Analyze sentiment of text content
    Uses TextBlob if available, otherwise falls back to keyword-based analysis
    """
    
    # Positive words for pharma/business context
    POSITIVE_WORDS = [
        'growth', 'expansion', 'approval', 'success', 'partnership',
        'launch', 'profit', 'milestone', 'achievement', 'breakthrough',
        'innovation', 'leading', 'strong', 'positive', 'increase',
        'revenue', 'opportunity', 'winning', 'awarded', 'excellent',
    ]
    
    # Negative words for pharma/business context
    NEGATIVE_WORDS = [
        'recall', 'warning', 'failure', 'decline', 'loss', 'issue',
        'problem', 'shutdown', 'closure', 'lawsuit', 'penalty',
        'violation', 'deficiency', 'concern', 'risk', 'drop',
        'shortage', 'delay', 'rejected', 'suspended',
    ]
    
    def __init__(self):
        """Initialize sentiment analyzer"""
        self.use_textblob = TEXTBLOB_AVAILABLE
        if not self.use_textblob:
            import logging
            logging.getLogger(__name__).warning(
                "TextBlob not available. Using keyword-based sentiment analysis."
            )
    
    def analyze(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with 'polarity' (-1 to 1), 'subjectivity' (0 to 1), 'label'
        """
        if not text:
            return {'polarity': 0.0, 'subjectivity': 0.0, 'label': 'neutral'}
        
        if self.use_textblob:
            return self._analyze_with_textblob(text)
        else:
            return self._analyze_with_keywords(text)
    
    def _analyze_with_textblob(self, text: str) -> Dict[str, float]:
        """Use TextBlob for sentiment analysis"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Determine label
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'polarity': round(polarity, 3),
            'subjectivity': round(subjectivity, 3),
            'label': label,
        }
    
    def _analyze_with_keywords(self, text: str) -> Dict[str, float]:
        """Fallback keyword-based sentiment analysis"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = sum(1 for word in words if word in self.POSITIVE_WORDS)
        negative_count = sum(1 for word in words if word in self.NEGATIVE_WORDS)
        
        total = positive_count + negative_count
        if total == 0:
            polarity = 0.0
        else:
            polarity = (positive_count - negative_count) / total
        
        # Estimate subjectivity based on sentiment word density
        word_count = len(words)
        if word_count == 0:
            subjectivity = 0.0
        else:
            subjectivity = min(total / word_count * 5, 1.0)
        
        # Determine label
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'polarity': round(polarity, 3),
            'subjectivity': round(subjectivity, 3),
            'label': label,
        }
    
    def get_polarity(self, text: str) -> float:
        """Quick method to get just polarity score"""
        return self.analyze(text)['polarity']
    
    def get_label(self, text: str) -> str:
        """Quick method to get just sentiment label"""
        return self.analyze(text)['label']
    
    def is_negative(self, text: str) -> bool:
        """Check if text has negative sentiment"""
        return self.analyze(text)['polarity'] < -0.1
    
    def is_positive(self, text: str) -> bool:
        """Check if text has positive sentiment"""
        return self.analyze(text)['polarity'] > 0.1
