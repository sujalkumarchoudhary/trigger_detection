"""
Keyword Detector for identifying trigger phrases in text
"""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

from config.trigger_config import TRIGGER_KEYWORDS, ALL_TRIGGER_KEYWORDS


@dataclass
class KeywordMatch:
    """Result of a keyword match"""
    keyword: str
    category: str
    position: int
    context: str  # Surrounding text


class KeywordDetector:
    """
    Detect trigger keywords and phrases in text
    """
    
    def __init__(self, custom_keywords: Dict[str, List[str]] = None):
        """
        Initialize keyword detector
        
        Args:
            custom_keywords: Optional custom keyword dictionary
        """
        self.keywords = custom_keywords or TRIGGER_KEYWORDS
        self.all_keywords = [kw for keywords in self.keywords.values() for kw in keywords]
        
        # Pre-compile regex patterns for efficiency
        self._patterns = {}
        for category, keywords in self.keywords.items():
            patterns = [re.compile(rf'\b{re.escape(kw)}\b', re.IGNORECASE) for kw in keywords]
            self._patterns[category] = list(zip(keywords, patterns))
    
    def detect(self, text: str) -> List[KeywordMatch]:
        """
        Detect all trigger keywords in text
        
        Args:
            text: Text to search
            
        Returns:
            List of KeywordMatch objects
        """
        if not text:
            return []
        
        matches = []
        
        for category, keyword_patterns in self._patterns.items():
            for keyword, pattern in keyword_patterns:
                for match in pattern.finditer(text):
                    # Get surrounding context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    matches.append(KeywordMatch(
                        keyword=keyword,
                        category=category,
                        position=match.start(),
                        context=context.strip(),
                    ))
        
        return matches
    
    def detect_categories(self, text: str) -> Dict[str, List[str]]:
        """
        Get keywords found grouped by category
        
        Args:
            text: Text to search
            
        Returns:
            Dict mapping category to list of found keywords
        """
        matches = self.detect(text)
        
        result = {}
        for match in matches:
            if match.category not in result:
                result[match.category] = []
            if match.keyword not in result[match.category]:
                result[match.category].append(match.keyword)
        
        return result
    
    def count_matches(self, text: str) -> int:
        """
        Count total number of keyword matches
        
        Args:
            text: Text to search
            
        Returns:
            Number of matches
        """
        return len(self.detect(text))
    
    def has_trigger(self, text: str) -> bool:
        """
        Check if text contains any trigger keywords
        
        Args:
            text: Text to search
            
        Returns:
            True if any triggers found
        """
        return self.count_matches(text) > 0
    
    def get_matched_keywords(self, text: str) -> List[str]:
        """
        Get list of unique matched keywords
        
        Args:
            text: Text to search
            
        Returns:
            List of unique keywords found
        """
        matches = self.detect(text)
        return list(set(match.keyword for match in matches))
    
    def score_relevance(self, text: str) -> float:
        """
        Calculate relevance score based on keyword matches (0-10)
        
        Args:
            text: Text to analyze
            
        Returns:
            Relevance score
        """
        matches = self.detect(text)
        
        if not matches:
            return 0.0
        
        # Count unique keywords and categories
        unique_keywords = set(m.keyword for m in matches)
        unique_categories = set(m.category for m in matches)
        
        # Score: more keywords and categories = higher score
        keyword_score = min(len(unique_keywords) * 1.5, 5.0)
        category_score = min(len(unique_categories) * 1.5, 5.0)
        
        return round(keyword_score + category_score, 1)
