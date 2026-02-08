"""
Utility functions for Trigger Detection System
"""
import re
import hashlib
import requests
from datetime import datetime
from typing import Optional
import time
import logging

from config.trigger_config import RATE_LIMIT_DELAY, MAX_RETRIES, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Clean and normalize text for analysis
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?\'"-]', '', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_company_name(text: str) -> Optional[str]:
    """
    Extract company name from text using common patterns
    
    Args:
        text: Text containing company name
        
    Returns:
        Extracted company name or None
    """
    if not text:
        return None
    
    # Common pharma company suffixes
    suffixes = [
        r'(?:Pharma(?:ceuticals?)?)',
        r'(?:Life ?Sciences?)',
        r'(?:Labs?(?:oratories?)?)',
        r'(?:Healthcare)',
        r'(?:Biotech)',
        r'(?:Ltd\.?)',
        r'(?:Pvt\.?)',
        r'(?:Limited)',
        r'(?:Private)',
        r'(?:Inc\.?)',
        r'(?:Corp(?:oration)?\.?)',
    ]
    
    # Pattern to match company names
    suffix_pattern = '|'.join(suffixes)
    pattern = rf'([A-Z][A-Za-z\s&\'-]+(?:{suffix_pattern})(?:\s+(?:{suffix_pattern}))*)'
    
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    if matches:
        # Return the longest match (most likely to be complete company name)
        return max(matches, key=len).strip()
    
    return None


def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse various date formats to datetime object
    
    Args:
        date_string: Date string in various formats
        
    Returns:
        datetime object or None
    """
    if not date_string:
        return None
    
    # Common date formats
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S%z',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
        '%a, %d %b %Y %H:%M:%S %z',  # RSS format
        '%a, %d %b %Y %H:%M:%S GMT',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    
    # Try parsing with dateutil if available
    try:
        from dateutil import parser
        return parser.parse(date_string)
    except (ImportError, ValueError):
        pass
    
    return None


def safe_request(
    url: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    params: Optional[dict] = None,
    data: Optional[dict] = None,
    retries: int = MAX_RETRIES,
) -> Optional[requests.Response]:
    """
    Make HTTP request with retry logic and rate limiting
    
    Args:
        url: URL to request
        method: HTTP method
        headers: Request headers
        params: Query parameters
        data: Request body
        retries: Number of retries
        
    Returns:
        Response object or None
    """
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    if headers:
        default_headers.update(headers)
    
    for attempt in range(retries):
        try:
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            
            response = requests.request(
                method=method,
                url=url,
                headers=default_headers,
                params=params,
                data=data,
                timeout=REQUEST_TIMEOUT,
            )
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {url} - {e}")
            
            if attempt < retries - 1:
                # Exponential backoff
                time.sleep(RATE_LIMIT_DELAY * (2 ** attempt))
            else:
                logger.error(f"All retries failed for: {url}")
                return None
    
    return None


def hash_content(content: str) -> str:
    """
    Generate MD5 hash of content for deduplication
    
    Args:
        content: Content to hash
        
    Returns:
        MD5 hash string
    """
    if not content:
        return ""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def extract_urls(text: str) -> list[str]:
    """
    Extract URLs from text
    
    Args:
        text: Text containing URLs
        
    Returns:
        List of URLs
    """
    if not text:
        return []
    
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
    return re.findall(url_pattern, text)


def extract_emails(text: str) -> list[str]:
    """
    Extract email addresses from text
    
    Args:
        text: Text containing emails
        
    Returns:
        List of email addresses
    """
    if not text:
        return []
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(email_pattern, text)))


def format_currency_inr(amount: float) -> str:
    """
    Format number as Indian Rupee currency
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted string (e.g., "₹1,23,456")
    """
    if amount >= 10000000:  # 1 Crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 Lakh
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.0f}"


def calculate_trigger_score(
    keyword_matches: int,
    sentiment_score: float,
    recency_days: int,
    source_reliability: float = 0.5
) -> float:
    """
    Calculate overall trigger importance score (0-10)
    
    Args:
        keyword_matches: Number of trigger keywords found
        sentiment_score: Sentiment score (-1 to 1)
        recency_days: Days since trigger detected
        source_reliability: Source reliability (0-1)
        
    Returns:
        Trigger score (0-10)
    """
    # Base score from keyword matches (0-4 points)
    keyword_score = min(keyword_matches * 1.0, 4.0)
    
    # Sentiment contribution (0-2 points)
    # Negative news about competitors is positive for us
    sentiment_contribution = 1.0 + sentiment_score  # Maps -1..1 to 0..2
    
    # Recency score (0-2 points)
    if recency_days <= 1:
        recency_score = 2.0
    elif recency_days <= 7:
        recency_score = 1.5
    elif recency_days <= 30:
        recency_score = 1.0
    else:
        recency_score = 0.5
    
    # Source reliability (0-2 points)
    reliability_score = source_reliability * 2.0
    
    # Total score
    total = keyword_score + sentiment_contribution + recency_score + reliability_score
    
    # Normalize to 0-10
    return min(round(total, 1), 10.0)
