"""
News & Event Monitor
Monitors RSS feeds, Google News, and performs keyword/sentiment analysis
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

from .base_monitor import BaseMonitor, TriggerResult
from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.keyword_detector import KeywordDetector
from config.trigger_config import RSS_FEEDS, SERPAPI_KEY, PHARMA_COMPANIES_TO_TRACK
from utils.helpers import (
    clean_text, extract_company_name, parse_date, 
    safe_request, hash_content, calculate_trigger_score
)

logger = logging.getLogger(__name__)


class NewsMonitor(BaseMonitor):
    """
    Monitor news sources for pharma industry triggers
    
    Features:
    - RSS Feed Aggregator (PharmaBiz, Business Standard, MoneyControl)
    - Google News API (via SerpAPI)
    - Keyword Alert System
    - Sentiment Analyzer
    """
    
    def __init__(self):
        super().__init__(name="NewsMonitor", source_type="news")
        self.sentiment_analyzer = SentimentAnalyzer()
        self.keyword_detector = KeywordDetector()
        self.seen_hashes = set()  # For deduplication
    
    def fetch(self) -> Dict[str, Any]:
        """Fetch news from all sources"""
        data = {
            'rss_items': [],
            'google_news': [],
        }
        
        # Fetch RSS feeds
        if FEEDPARSER_AVAILABLE:
            for source_name, feed_url in RSS_FEEDS.items():
                try:
                    self.logger.debug(f"Fetching RSS: {source_name}")
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:20]:  # Limit to 20 per feed
                        data['rss_items'].append({
                            'source': source_name,
                            'title': entry.get('title', ''),
                            'summary': entry.get('summary', ''),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                        })
                        
                except Exception as e:
                    self.logger.warning(f"Failed to fetch RSS {source_name}: {e}")
        else:
            self.logger.warning("feedparser not available - skipping RSS feeds")
        
        # Fetch Google News via SerpAPI
        if SERPAPI_KEY:
            data['google_news'] = self._fetch_google_news()
        else:
            self.logger.info("No SerpAPI key - skipping Google News")
        
        return data
    
    def _fetch_google_news(self) -> List[Dict]:
        """Fetch pharma news from Google News via SerpAPI"""
        news_items = []
        
        # Search queries
        queries = [
            "pharma manufacturing partner India",
            "pharmaceutical outsourcing India",
            "drug approval CDSCO India",
            "pharma capacity expansion India",
        ]
        
        # Add company-specific searches
        for company in PHARMA_COMPANIES_TO_TRACK[:5]:  # Limit to top 5
            queries.append(f'"{company}" manufacturing news')
        
        for query in queries:
            try:
                response = safe_request(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google_news",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "gl": "in",  # India
                    }
                )
                
                if response and response.status_code == 200:
                    result = response.json()
                    for item in result.get('news_results', [])[:10]:
                        news_items.append({
                            'source': 'google_news',
                            'query': query,
                            'title': item.get('title', ''),
                            'snippet': item.get('snippet', ''),
                            'link': item.get('link', ''),
                            'date': item.get('date', ''),
                            'source_name': item.get('source', {}).get('name', ''),
                        })
                        
            except Exception as e:
                self.logger.warning(f"Google News fetch failed for '{query}': {e}")
        
        return news_items
    
    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse raw news data into structured format"""
        items = []
        
        # Process RSS items
        for item in raw_data.get('rss_items', []):
            content = f"{item['title']} {item['summary']}"
            content_hash = hash_content(content)
            
            # Skip duplicates
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': f"rss_{item['source']}",
                'title': clean_text(item['title']),
                'content': clean_text(item['summary']),
                'url': item['link'],
                'published': parse_date(item['published']),
                'raw': item,
            })
        
        # Process Google News items
        for item in raw_data.get('google_news', []):
            content = f"{item['title']} {item['snippet']}"
            content_hash = hash_content(content)
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': f"google_news_{item.get('source_name', 'unknown')}",
                'title': clean_text(item['title']),
                'content': clean_text(item.get('snippet', '')),
                'url': item['link'],
                'published': parse_date(item.get('date', '')),
                'raw': item,
            })
        
        return items
    
    def analyze(self, items: List[Dict[str, Any]]) -> List[TriggerResult]:
        """Analyze news items for triggers"""
        results = []
        
        for item in items:
            full_text = f"{item['title']} {item['content']}"
            
            # Keyword detection
            matched_keywords = self.keyword_detector.get_matched_keywords(full_text)
            
            # Skip if no trigger keywords found
            if not matched_keywords:
                continue
            
            # Sentiment analysis
            sentiment = self.sentiment_analyzer.analyze(full_text)
            
            # Extract company name
            company_name = extract_company_name(full_text)
            
            # Calculate trigger score
            recency_days = 0
            if item.get('published'):
                recency_days = (datetime.now() - item['published']).days
            
            trigger_score = calculate_trigger_score(
                keyword_matches=len(matched_keywords),
                sentiment_score=sentiment['polarity'],
                recency_days=recency_days,
                source_reliability=0.7,  # News sources generally reliable
            )
            
            results.append(TriggerResult(
                source_type=self.source_type,
                source_name=item['source'],
                title=item['title'],
                content=item['content'][:500],  # Limit content length
                url=item['url'],
                company_name=company_name,
                trigger_keywords=matched_keywords,
                sentiment_score=sentiment['polarity'],
                trigger_score=trigger_score,
                detected_at=datetime.now(),
                published_at=item.get('published'),
                raw_data=item['raw'],
            ))
        
        # Sort by trigger score (highest first)
        results.sort(key=lambda x: x.trigger_score, reverse=True)
        
        return results
