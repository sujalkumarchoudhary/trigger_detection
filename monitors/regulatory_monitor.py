"""
Regulatory Change Detector
Uses SerpAPI Google Search for CDSCO approvals, FDA alerts, and patent news
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
import logging

from .base_monitor import BaseMonitor, TriggerResult
from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.keyword_detector import KeywordDetector
from config.trigger_config import SERPAPI_KEY
from utils.helpers import (
    clean_text, extract_company_name, parse_date,
    safe_request, hash_content, calculate_trigger_score
)

logger = logging.getLogger(__name__)


class RegulatoryMonitor(BaseMonitor):
    """
    Monitor regulatory sources for pharma triggers using SerpAPI
    
    Features:
    - CDSCO Approval News (via Google Search)
    - FDA Alert News (via Google Search)
    - Patent Grant News (via Google Search)
    """
    
    def __init__(self):
        super().__init__(name="RegulatoryMonitor", source_type="regulatory")
        self.sentiment_analyzer = SentimentAnalyzer()
        self.keyword_detector = KeywordDetector()
        self.seen_hashes = set()
    
    def fetch(self) -> Dict[str, Any]:
        """Fetch regulatory data using SerpAPI Google Search"""
        data = {
            'cdsco': [],
            'fda_alerts': [],
            'patents': [],
        }
        
        if not SERPAPI_KEY:
            self.logger.warning("No SerpAPI key - regulatory monitoring limited")
            return data
        
        # Fetch CDSCO approvals via Google News
        data['cdsco'] = self._fetch_cdsco_news()
        
        # Fetch FDA alerts via Google News
        data['fda_alerts'] = self._fetch_fda_news()
        
        # Fetch patent information via Google News
        data['patents'] = self._fetch_patent_news()
        
        return data
    
    def _fetch_cdsco_news(self) -> List[Dict]:
        """Fetch CDSCO approval news via SerpAPI"""
        results = []
        
        queries = [
            "CDSCO drug approval India",
            "DCGI approval pharmaceutical India",
            "new drug approval India CDSCO",
            "CDSCO license pharmaceutical",
        ]
        
        for query in queries:
            try:
                response = safe_request(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_news",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "gl": "in",
                        "num": 10,
                    }
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    for item in data.get('news_results', [])[:10]:
                        results.append({
                            'source': 'cdsco_news',
                            'title': item.get('title', ''),
                            'snippet': item.get('snippet', ''),
                            'url': item.get('link', ''),
                            'date': item.get('date', ''),
                            'source_name': item.get('source', {}).get('name', ''),
                            'type': 'drug_approval',
                        })
                        
            except Exception as e:
                self.logger.warning(f"CDSCO news fetch failed for '{query}': {e}")
        
        return results
    
    def _fetch_fda_news(self) -> List[Dict]:
        """Fetch FDA alert news via SerpAPI"""
        results = []
        
        queries = [
            "FDA warning letter India pharmaceutical",
            "FDA import alert India drug",
            "FDA 483 observations India pharma",
            "FDA inspection pharmaceutical India",
        ]
        
        for query in queries:
            try:
                response = safe_request(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_news",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "gl": "us",
                        "num": 10,
                    }
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    for item in data.get('news_results', [])[:10]:
                        results.append({
                            'source': 'fda_news',
                            'title': item.get('title', ''),
                            'snippet': item.get('snippet', ''),
                            'url': item.get('link', ''),
                            'date': item.get('date', ''),
                            'source_name': item.get('source', {}).get('name', ''),
                            'type': 'fda_alert',
                            'severity': 'high' if 'warning' in item.get('title', '').lower() else 'medium',
                        })
                        
            except Exception as e:
                self.logger.warning(f"FDA news fetch failed for '{query}': {e}")
        
        return results
    
    def _fetch_patent_news(self) -> List[Dict]:
        """Fetch pharmaceutical patent news via SerpAPI"""
        results = []
        
        queries = [
            "pharmaceutical patent India granted",
            "drug patent approval India",
            "pharma patent expires India",
        ]
        
        for query in queries:
            try:
                response = safe_request(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_news",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "gl": "in",
                        "num": 5,
                    }
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    for item in data.get('news_results', [])[:5]:
                        results.append({
                            'source': 'patent_news',
                            'title': item.get('title', ''),
                            'snippet': item.get('snippet', ''),
                            'url': item.get('link', ''),
                            'date': item.get('date', ''),
                            'source_name': item.get('source', {}).get('name', ''),
                            'type': 'patent',
                        })
                        
            except Exception as e:
                self.logger.warning(f"Patent news fetch failed for '{query}': {e}")
        
        return results
    
    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse regulatory data into structured format"""
        items = []
        
        # Process CDSCO news
        for item in raw_data.get('cdsco', []):
            content = f"{item.get('title', '')} {item.get('snippet', '')}"
            content_hash = hash_content(content)
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': item['source'],
                'title': clean_text(item.get('title', 'Unknown Approval')),
                'content': clean_text(item.get('snippet', '')),
                'url': item.get('url', ''),
                'company': extract_company_name(content),
                'date': parse_date(item.get('date', '')),
                'reg_type': 'approval',
                'severity': 'positive',
                'raw': item,
            })
        
        # Process FDA news
        for item in raw_data.get('fda_alerts', []):
            content = f"{item.get('title', '')} {item.get('snippet', '')}"
            content_hash = hash_content(content)
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': item['source'],
                'title': clean_text(item.get('title', 'Unknown Alert')),
                'content': clean_text(item.get('snippet', '')),
                'url': item.get('url', ''),
                'company': extract_company_name(content),
                'date': parse_date(item.get('date', '')),
                'reg_type': item.get('type', 'fda_alert'),
                'severity': item.get('severity', 'medium'),
                'raw': item,
            })
        
        # Process patent news
        for item in raw_data.get('patents', []):
            content = f"{item.get('title', '')} {item.get('snippet', '')}"
            content_hash = hash_content(content)
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': 'patent_news',
                'title': clean_text(item.get('title', 'Patent News')),
                'content': clean_text(item.get('snippet', '')),
                'url': item.get('url', ''),
                'company': extract_company_name(content),
                'date': parse_date(item.get('date', '')),
                'reg_type': 'patent',
                'severity': 'neutral',
                'raw': item,
            })
        
        return items
    
    def analyze(self, items: List[Dict[str, Any]]) -> List[TriggerResult]:
        """Analyze regulatory items for triggers"""
        results = []
        
        for item in items:
            full_text = f"{item['title']} {item['content']}"
            
            # Keyword detection
            matched_keywords = self.keyword_detector.get_matched_keywords(full_text)
            
            # Add regulatory-specific keywords
            if 'cdsco' in item['source'].lower() or 'approval' in full_text.lower():
                matched_keywords.append('product_approval')
            if 'fda' in item['source'].lower():
                matched_keywords.append('fda_alert')
            if 'patent' in item['source'].lower():
                matched_keywords.append('patent_news')
            
            # Sentiment analysis
            sentiment = self.sentiment_analyzer.analyze(full_text)
            
            # For FDA alerts, flip sentiment (negative for them = opportunity for others)
            if 'fda' in item['source'].lower() and item.get('severity') == 'high':
                sentiment_score = -sentiment['polarity']  # Flip
                matched_keywords.append('competitor_issue')
            else:
                sentiment_score = sentiment['polarity']
            
            # Calculate trigger score
            recency_days = 0
            if item.get('date'):
                recency_days = (datetime.now() - item['date']).days
            
            # Regulatory items are high value
            source_reliability = 0.85
            
            trigger_score = calculate_trigger_score(
                keyword_matches=len(matched_keywords) + 1,  # +1 for being regulatory
                sentiment_score=sentiment_score,
                recency_days=recency_days,
                source_reliability=source_reliability,
            )
            
            results.append(TriggerResult(
                source_type=self.source_type,
                source_name=item['source'],
                title=item['title'],
                content=item['content'][:500],
                url=item['url'],
                company_name=item.get('company'),
                trigger_keywords=list(set(matched_keywords)),
                sentiment_score=sentiment_score,
                trigger_score=trigger_score,
                detected_at=datetime.now(),
                published_at=item.get('date'),
                raw_data=item['raw'],
            ))
        
        # Sort by trigger score
        results.sort(key=lambda x: x.trigger_score, reverse=True)
        
        return results
