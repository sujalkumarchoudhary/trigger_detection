"""
Financial & Growth Indicator Monitor
Monitors quarterly results, stock filings, job postings, and social media
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
import logging

from bs4 import BeautifulSoup

from .base_monitor import BaseMonitor, TriggerResult
from analyzers.sentiment_analyzer import SentimentAnalyzer
from analyzers.keyword_detector import KeywordDetector
from config.trigger_config import (
    FINANCIAL_SOURCES, JOB_SOURCES, 
    PHARMA_COMPANIES_TO_TRACK, SERPAPI_KEY
)
from utils.helpers import (
    clean_text, extract_company_name, parse_date,
    safe_request, hash_content, calculate_trigger_score
)

logger = logging.getLogger(__name__)


class FinancialMonitor(BaseMonitor):
    """
    Monitor financial indicators for pharma outsourcing signals
    
    Features:
    - Quarterly Results Scraper
    - Stock Exchange Filings Parser
    - Job Posting Analyzer
    - Social Media Monitor
    """
    
    def __init__(self):
        super().__init__(name="FinancialMonitor", source_type="financial")
        self.sentiment_analyzer = SentimentAnalyzer()
        self.keyword_detector = KeywordDetector()
        self.seen_hashes = set()
    
    def fetch(self) -> Dict[str, Any]:
        """Fetch financial data from all sources"""
        data = {
            'quarterly_results': [],
            'stock_filings': [],
            'job_postings': [],
            'social_media': [],
        }
        
        # Fetch quarterly results/announcements
        data['quarterly_results'] = self._fetch_quarterly_results()
        
        # Fetch stock exchange filings
        data['stock_filings'] = self._fetch_stock_filings()
        
        # Fetch job postings
        data['job_postings'] = self._fetch_job_postings()
        
        # Fetch social media mentions
        data['social_media'] = self._fetch_social_media()
        
        return data
    
    def _fetch_quarterly_results(self) -> List[Dict]:
        """Fetch quarterly results and future plans from financial reports"""
        results = []
        
        # Try multiple Screener.in URLs (screen IDs can change)
        screener_urls = [
            "https://www.screener.in/screens/71/pharma-companies/",
            "https://www.screener.in/screens/23505/pharma-companies/",
        ]
        
        screener_success = False
        for screener_url in screener_urls:
            try:
                response = safe_request(screener_url, retries=1)
                if response:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for company results
                    table = soup.find('table')
                    if table:
                        rows = table.find_all('tr')
                        for row in rows[1:30]:  # Limit to 30 companies
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                company_link = cells[0].find('a')
                                company_name = clean_text(company_link.get_text()) if company_link else ''
                                
                                results.append({
                                    'source': 'screener',
                                    'company': company_name,
                                    'market_cap': clean_text(cells[1].get_text()) if len(cells) > 1 else '',
                                    'sales_growth': clean_text(cells[2].get_text()) if len(cells) > 2 else '',
                                    'profit_growth': clean_text(cells[3].get_text()) if len(cells) > 3 else '',
                                    'url': company_link.get('href', screener_url) if company_link else screener_url,
                                })
                        if results:
                            screener_success = True
                            break  # Got data, stop trying other URLs
                            
            except Exception as e:
                self.logger.debug(f"Screener fetch failed for {screener_url}: {e}")
        
        # Fallback: MoneyControl pharma RSS for financial news
        if not screener_success:
            self.logger.info("Screener failed, trying MoneyControl RSS fallback")
            try:
                import feedparser
                feed = feedparser.parse("https://www.moneycontrol.com/rss/pharma.xml")
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    full_text = f"{title} {summary}"
                    
                    # Filter for financial/growth indicators
                    if any(kw in full_text.lower() for kw in 
                           ['result', 'revenue', 'profit', 'growth', 'expansion', 
                            'capex', 'capacity', 'revenue', 'quarter', 'annual']):
                        results.append({
                            'source': 'moneycontrol_rss',
                            'company': extract_company_name(full_text) or 'Unknown',
                            'announcement': clean_text(f"{title}. {summary}")[:300],
                            'url': entry.get('link', ''),
                        })
            except Exception as e:
                self.logger.warning(f"MoneyControl RSS fallback failed: {e}")
        
        # BSE corporate filings
        bse_url = "https://www.bseindia.com/corporates/ann.html"
        
        try:
            response = safe_request(bse_url)
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for announcements
                announcements = soup.find_all(['tr', 'div'], class_=re.compile(r'ann|result', re.I))
                for ann in announcements[:20]:
                    text = clean_text(ann.get_text())
                    
                    # Filter for pharma and expansion-related
                    if any(kw in text.lower() for kw in 
                           ['pharma', 'pharmaceutical', 'drug', 'medicine']):
                        if any(kw in text.lower() for kw in 
                               ['expansion', 'capacity', 'capex', 'future', 'outlook', 'guidance']):
                            results.append({
                                'source': 'bse',
                                'company': extract_company_name(text) or 'Unknown',
                                'announcement': text[:300],
                                'url': bse_url,
                            })
                            
        except Exception as e:
            self.logger.debug(f"BSE fetch failed: {e}")
        
        return results
    
    def _fetch_stock_filings(self) -> List[Dict]:
        """Fetch stock exchange filings for capacity expansion announcements"""
        filings = []
        
        # Monitor NSE announcements
        nse_url = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
        
        # Note: NSE requires special handling due to API protection
        # Using alternative approach via SerpAPI if available
        
        if SERPAPI_KEY:
            search_queries = [
                "site:nseindia.com pharma capacity expansion announcement",
                "site:bseindia.com pharmaceutical capex announcement",
            ]
            
            for query in search_queries:
                try:
                    response = safe_request(
                        "https://serpapi.com/search",
                        params={
                            "engine": "google",
                            "q": query,
                            "api_key": SERPAPI_KEY,
                            "num": 10,
                        }
                    )
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        for result in data.get('organic_results', []):
                            filings.append({
                                'source': 'stock_filing',
                                'title': result.get('title', ''),
                                'snippet': result.get('snippet', ''),
                                'url': result.get('link', ''),
                            })
                            
                except Exception as e:
                    self.logger.debug(f"Stock filing search failed: {e}")
        
        return filings
    
    def _fetch_job_postings(self) -> List[Dict]:
        """
        Analyze job postings to detect outsourcing signals
        Pattern: Hiring sales/marketing but NOT manufacturing = likely outsourcing
        """
        postings = []
        
        # Track companies with job posting patterns
        for company in PHARMA_COMPANIES_TO_TRACK[:10]:
            company_jobs = {
                'company': company,
                'sales_jobs': 0,
                'manufacturing_jobs': 0,
                'total_jobs': 0,
                'outsourcing_signal': False,
            }
            
            if SERPAPI_KEY:
                # Search for company jobs
                try:
                    response = safe_request(
                        "https://serpapi.com/search",
                        params={
                            "engine": "google_jobs",
                            "q": f"{company} pharmaceutical India",
                            "api_key": SERPAPI_KEY,
                        }
                    )
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        jobs = data.get('jobs_results', [])
                        
                        company_jobs['total_jobs'] = len(jobs)
                        
                        for job in jobs:
                            title = job.get('title', '').lower()
                            
                            # Categorize job
                            if any(kw in title for kw in 
                                   ['sales', 'marketing', 'business development', 'mr ', 'medical representative']):
                                company_jobs['sales_jobs'] += 1
                            elif any(kw in title for kw in 
                                     ['production', 'manufacturing', 'plant', 'operator', 'quality control', 'qc', 'qa']):
                                company_jobs['manufacturing_jobs'] += 1
                        
                        # Detect outsourcing signal
                        if (company_jobs['sales_jobs'] > 3 and 
                            company_jobs['manufacturing_jobs'] == 0 and
                            company_jobs['total_jobs'] >= 5):
                            company_jobs['outsourcing_signal'] = True
                            
                except Exception as e:
                    self.logger.debug(f"Job search failed for {company}: {e}")
            
            if company_jobs['total_jobs'] > 0:
                postings.append(company_jobs)
        
        return postings
    
    def _fetch_social_media(self) -> List[Dict]:
        """Monitor company social media for expansion announcements"""
        social_posts = []
        
        # LinkedIn company pages via SerpAPI
        if SERPAPI_KEY:
            for company in PHARMA_COMPANIES_TO_TRACK[:5]:
                try:
                    response = safe_request(
                        "https://serpapi.com/search",
                        params={
                            "engine": "google",
                            "q": f'site:linkedin.com "{company}" expansion OR "new facility" OR "manufacturing partnership"',
                            "api_key": SERPAPI_KEY,
                            "num": 5,
                        }
                    )
                    
                    if response and response.status_code == 200:
                        data = response.json()
                        for result in data.get('organic_results', []):
                            social_posts.append({
                                'source': 'linkedin',
                                'company': company,
                                'title': result.get('title', ''),
                                'snippet': result.get('snippet', ''),
                                'url': result.get('link', ''),
                            })
                            
                except Exception as e:
                    self.logger.debug(f"Social media search failed for {company}: {e}")
        
        return social_posts
    
    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse financial data into structured format"""
        items = []
        
        # Process quarterly results
        for result in raw_data.get('quarterly_results', []):
            content_hash = hash_content(f"{result.get('company', '')}_{result.get('announcement', '')}")
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': result.get('source', 'financial'),
                'title': f"{result.get('company', 'Company')} Financial Update",
                'content': result.get('announcement', f"Sales Growth: {result.get('sales_growth', 'N/A')}"),
                'company': result.get('company', ''),
                'url': result.get('url', ''),
                'data_type': 'quarterly_result',
                'raw': result,
            })
        
        # Process stock filings
        for filing in raw_data.get('stock_filings', []):
            content_hash = hash_content(filing.get('title', ''))
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': filing.get('source', 'stock_filing'),
                'title': filing.get('title', 'Stock Filing'),
                'content': filing.get('snippet', ''),
                'company': extract_company_name(filing.get('title', '')),
                'url': filing.get('url', ''),
                'data_type': 'stock_filing',
                'raw': filing,
            })
        
        # Process job postings with outsourcing signal
        for posting in raw_data.get('job_postings', []):
            if posting.get('outsourcing_signal'):
                items.append({
                    'source': 'job_analysis',
                    'title': f"{posting['company']} - Outsourcing Signal Detected",
                    'content': f"Hiring {posting['sales_jobs']} sales roles, 0 manufacturing roles",
                    'company': posting['company'],
                    'url': '',
                    'data_type': 'job_signal',
                    'raw': posting,
                })
        
        # Process social media
        for post in raw_data.get('social_media', []):
            content_hash = hash_content(post.get('title', ''))
            
            if content_hash in self.seen_hashes:
                continue
            self.seen_hashes.add(content_hash)
            
            items.append({
                'source': post.get('source', 'social'),
                'title': post.get('title', 'Social Media Post'),
                'content': post.get('snippet', ''),
                'company': post.get('company', ''),
                'url': post.get('url', ''),
                'data_type': 'social_media',
                'raw': post,
            })
        
        return items
    
    def analyze(self, items: List[Dict[str, Any]]) -> List[TriggerResult]:
        """Analyze financial indicators for triggers"""
        results = []
        
        for item in items:
            full_text = f"{item['title']} {item['content']}"
            
            # Keyword detection
            matched_keywords = self.keyword_detector.get_matched_keywords(full_text)
            
            # Sentiment analysis
            sentiment = self.sentiment_analyzer.analyze(full_text)
            
            # Special handling for job signal
            if item.get('data_type') == 'job_signal':
                matched_keywords.append('job_outsourcing_signal')
                trigger_score = 8.0  # High value signal
            else:
                # Calculate trigger score
                trigger_score = calculate_trigger_score(
                    keyword_matches=len(matched_keywords),
                    sentiment_score=sentiment['polarity'],
                    recency_days=7,  # Assume recent
                    source_reliability=0.6,
                )
            
            # Only include if there are triggers or it's a job signal
            if matched_keywords or item.get('data_type') == 'job_signal':
                results.append(TriggerResult(
                    source_type=self.source_type,
                    source_name=item['source'],
                    title=item['title'],
                    content=item['content'][:500],
                    url=item['url'],
                    company_name=item.get('company'),
                    trigger_keywords=matched_keywords,
                    sentiment_score=sentiment['polarity'],
                    trigger_score=trigger_score,
                    detected_at=datetime.now(),
                    published_at=None,
                    raw_data=item['raw'],
                ))
        
        # Sort by trigger score
        results.sort(key=lambda x: x.trigger_score, reverse=True)
        
        return results
