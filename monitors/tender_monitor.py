"""
Tender & Contract Monitor
Uses SerpAPI Google Search for government and hospital tenders
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
import logging

from .base_monitor import BaseMonitor, TriggerResult
from analyzers.keyword_detector import KeywordDetector
from analyzers.quantity_analyzer import QuantityAnalyzer
from config.trigger_config import SERPAPI_KEY
from utils.helpers import (
    clean_text, extract_company_name, parse_date,
    safe_request, hash_content, calculate_trigger_score
)

logger = logging.getLogger(__name__)


class TenderMonitor(BaseMonitor):
    """
    Monitor tender sources for pharma outsourcing opportunities using SerpAPI
    
    Features:
    - Government Tender News (GEM, CPPP via Google Search)
    - Hospital Tender News (via Google Search)
    - Quantity Analysis
    """
    
    def __init__(self):
        super().__init__(name="TenderMonitor", source_type="tender")
        self.keyword_detector = KeywordDetector()
        self.quantity_analyzer = QuantityAnalyzer()
        self.seen_hashes = set()
    
    def fetch(self) -> Dict[str, Any]:
        """Fetch tender data using SerpAPI Google Search + free RSS fallbacks"""
        data = {
            'government_tenders': [],
            'hospital_tenders': [],
        }
        
        if SERPAPI_KEY:
            # Fetch government tender news
            data['government_tenders'] = self._fetch_govt_tender_news()
            
            # Fetch hospital tender news  
            data['hospital_tenders'] = self._fetch_hospital_tender_news()
        else:
            self.logger.warning("No SerpAPI key - using free RSS fallbacks for tender monitoring")
        
        # Always try free RSS fallbacks (supplements SerpAPI or replaces it)
        rss_results = self._fetch_tender_rss()
        data['government_tenders'].extend(rss_results)
        
        return data
    
    def _fetch_tender_rss(self) -> List[Dict]:
        """Fetch tender news from free RSS feeds (no API key needed)"""
        results = []
        
        try:
            import feedparser
        except ImportError:
            self.logger.warning("feedparser not available - skipping RSS fallbacks")
            return results
        
        # Free RSS feeds that may contain tender/procurement news
        rss_feeds = {
            'et_pharma': 'https://economictimes.indiatimes.com/industry/healthcare/biotech/pharmaceuticals/rssfeeds/13357808.cms',
            'bs_pharma': 'https://www.business-standard.com/rss/companies/pharma-172.rss',
            'livemint': 'https://www.livemint.com/rss/companies/pharma',
            'pharmabiz': 'http://www.pharmabiz.com/RSSFeed.aspx',
        }
        
        tender_keywords = [
            'tender', 'procurement', 'bid', 'contract', 'supply order',
            'gem portal', 'government supply', 'hospital supply', 'bulk drug',
            'rate contract', 'purchase order', 'empanelment', 'auction',
        ]
        
        for source_name, feed_url in rss_feeds.items():
            try:
                self.logger.debug(f"Fetching tender RSS: {source_name}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    full_text = f"{title} {summary}".lower()
                    
                    # Filter for tender-relevant content
                    if any(kw in full_text for kw in tender_keywords):
                        results.append({
                            'source': f'rss_{source_name}_tender',
                            'title': title,
                            'snippet': summary,
                            'url': entry.get('link', ''),
                            'date': entry.get('published', ''),
                            'displayed_link': source_name,
                            'type': 'government_tender',
                        })
                        
            except Exception as e:
                self.logger.debug(f"RSS fetch failed for {source_name}: {e}")
        
        self.logger.info(f"RSS fallback found {len(results)} tender items")
        return results
    
    def _fetch_govt_tender_news(self) -> List[Dict]:
        """Fetch government pharmaceutical tender news via SerpAPI"""
        results = []
        
        queries = [
            "pharmaceutical tender India GEM portal",
            "drug tender India government",
            "medical supplies tender India",
            "pharma tender CPPP India",
            "bulk drug tender India government",
        ]
        
        for query in queries:
            try:
                response = safe_request(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "gl": "in",
                        "num": 10,
                        "tbs": "qdr:m",  # Last month
                    }
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    
                    # Process organic results
                    for item in data.get('organic_results', [])[:10]:
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        
                        # Filter for relevant results
                        if any(kw in title.lower() or kw in snippet.lower() 
                               for kw in ['tender', 'bid', 'contract', 'supply', 'procurement']):
                            results.append({
                                'source': 'govt_tender_search',
                                'title': title,
                                'snippet': snippet,
                                'url': item.get('link', ''),
                                'displayed_link': item.get('displayed_link', ''),
                                'type': 'government_tender',
                            })
                            
            except Exception as e:
                self.logger.warning(f"Govt tender search failed for '{query}': {e}")
        
        # Also try Google News for tender announcements
        news_queries = [
            "pharmaceutical tender awarded India",
            "medicine supply contract India",
        ]
        
        for query in news_queries:
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
                            'source': 'tender_news',
                            'title': item.get('title', ''),
                            'snippet': item.get('snippet', ''),
                            'url': item.get('link', ''),
                            'date': item.get('date', ''),
                            'source_name': item.get('source', {}).get('name', ''),
                            'type': 'tender_news',
                        })
                        
            except Exception as e:
                self.logger.warning(f"Tender news search failed for '{query}': {e}")
        
        return results
    
    def _fetch_hospital_tender_news(self) -> List[Dict]:
        """Fetch hospital pharmaceutical tender news via SerpAPI"""
        results = []
        
        queries = [
            "AIIMS pharmaceutical tender",
            "hospital medicine tender India",
            "ESI hospital drug tender",
            "government hospital medical supplies tender",
        ]
        
        for query in queries:
            try:
                response = safe_request(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "gl": "in",
                        "num": 10,
                        "tbs": "qdr:m",  # Last month
                    }
                )
                
                if response and response.status_code == 200:
                    data = response.json()
                    
                    for item in data.get('organic_results', [])[:10]:
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        
                        if any(kw in title.lower() or kw in snippet.lower() 
                               for kw in ['tender', 'bid', 'supply', 'hospital', 'medical']):
                            results.append({
                                'source': 'hospital_tender_search',
                                'title': title,
                                'snippet': snippet,
                                'url': item.get('link', ''),
                                'displayed_link': item.get('displayed_link', ''),
                                'type': 'hospital_tender',
                            })
                            
            except Exception as e:
                self.logger.warning(f"Hospital tender search failed for '{query}': {e}")
        
        return results
    
    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse tender data into structured format"""
        items = []
        
        # Process government tenders
        for item in raw_data.get('government_tenders', []):
            content = f"{item.get('title', '')} {item.get('snippet', '')}"
            content_hash = hash_content(content)
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            # Try to extract quantity info
            quantity_info = self.quantity_analyzer.analyze_tender(content)
            
            items.append({
                'source': item['source'],
                'title': clean_text(item.get('title', 'Unknown Tender')),
                'content': clean_text(item.get('snippet', '')),
                'url': item.get('url', ''),
                'organization': extract_company_name(content) or item.get('displayed_link', ''),
                'quantity_info': quantity_info,
                'date': parse_date(item.get('date', '')),
                'tender_type': 'government',
                'raw': item,
            })
        
        # Process hospital tenders
        for item in raw_data.get('hospital_tenders', []):
            content = f"{item.get('title', '')} {item.get('snippet', '')}"
            content_hash = hash_content(content)
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            quantity_info = self.quantity_analyzer.analyze_tender(content)
            
            items.append({
                'source': item['source'],
                'title': clean_text(item.get('title', 'Unknown Tender')),
                'content': clean_text(item.get('snippet', '')),
                'url': item.get('url', ''),
                'organization': extract_company_name(content) or item.get('displayed_link', ''),
                'quantity_info': quantity_info,
                'date': parse_date(item.get('date', '')),
                'tender_type': 'hospital',
                'raw': item,
            })
        
        return items
    
    def analyze(self, items: List[Dict[str, Any]]) -> List[TriggerResult]:
        """Analyze tender items for triggers"""
        results = []
        
        for item in items:
            full_text = f"{item['title']} {item['content']}"
            
            # Keyword detection
            matched_keywords = self.keyword_detector.get_matched_keywords(full_text)
            
            # Add tender-specific keywords
            matched_keywords.append('tender_opportunity')
            if item.get('quantity_info', {}).get('opportunity_score', 0) > 5:
                matched_keywords.append('high_volume_tender')
            
            # Calculate score based on quantity
            quantity_bonus = 0
            if item.get('quantity_info'):
                quantity_bonus = item['quantity_info'].get('opportunity_score', 0) / 10
            
            # Calculate trigger score
            recency_days = 7  # Default for tenders
            if item.get('date'):
                recency_days = (datetime.now() - item['date']).days
            
            trigger_score = calculate_trigger_score(
                keyword_matches=len(matched_keywords),
                sentiment_score=0.5 + quantity_bonus,  # Tenders are neutral-positive
                recency_days=recency_days,
                source_reliability=0.8,
            )
            
            results.append(TriggerResult(
                source_type=self.source_type,
                source_name=item['source'],
                title=item['title'],
                content=item['content'][:500],
                url=item['url'],
                company_name=item.get('organization'),
                trigger_keywords=list(set(matched_keywords)),
                sentiment_score=0.5,
                trigger_score=trigger_score,
                detected_at=datetime.now(),
                published_at=item.get('date'),
                raw_data=item['raw'],
            ))
        
        # Sort by trigger score
        results.sort(key=lambda x: x.trigger_score, reverse=True)
        
        return results
